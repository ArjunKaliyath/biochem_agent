# ----------------- Local Code Runner (sandboxed) -----------------
import asyncio, subprocess, uuid, ast, textwrap, tempfile, sys, os
from pathlib import Path
from tools.types import ToolResult, ToolResultType

ALLOWED_IMPORTS = {
    "pandas", "numpy",
    "matplotlib", "matplotlib.pyplot",
    "seaborn",
    "plotly", "plotly.express", "plotly.graph_objects",
    "math", "statistics", "json", "csv", "io"
}

DISALLOWED_NAMES = {
    "os", "sys", "subprocess", "shutil", "socket", "requests", "urllib",
    "pathlib", "builtins", "importlib", "ctypes"
}

def _validate_user_code(code: str) -> str | None:
    """Return error message if invalid, else None."""
    try:
        tree = ast.parse(code)
    except Exception as e:
        return f"Code did not parse: {e}"

    # Imports whitelist
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name  # e.g., 'pandas' or 'matplotlib.pyplot'
                if mod not in ALLOWED_IMPORTS:
                    return f"Import not allowed: {mod}"
                # also guard parents (e.g., 'matplotlib' is fine; a submodule should still be in list)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            fulls = {base} | {f"{base}.{alias.name}" for alias in node.names if base}
            for mod in fulls:
                if mod not in ALLOWED_IMPORTS:
                    return f"Import not allowed: {mod}"
        elif isinstance(node, ast.Name):
            if node.id in DISALLOWED_NAMES:
                return f"Identifier not allowed: {node.id}"
        elif isinstance(node, ast.Call):
            # Block built-in/file ops
            # Disallow open(...) unless clearly pandas read_* usage (which doesn't call open directly)
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id == "open":
                return "Direct file I/O via open() is not allowed. Use pandas.read_csv/read_json with provided paths."
    return None


async def run_code_sandboxed(code: str, timeout_sec: int, session_id: str) -> list[ToolResult]:
    """Execute code in isolated run dir with strict validations. Return list of ToolResult(s)."""
    err = _validate_user_code(code)
    if err:
        return [ToolResult(type=ToolResultType.text, error=True, content=err)]

    # run_root = Path("runs") / str(session_id)
    # run_root.mkdir(parents=True, exist_ok=True)
    # workdir = Path(tempfile.mkdtemp(prefix="code_run_", dir=run_root))

    base_dir = Path(__file__).resolve().parent.parent  # /app/tools -> /app
    runs_root = base_dir / "runs"
    runs_root.mkdir(exist_ok=True)

    session_dir = runs_root / session_id
    session_dir.mkdir(exist_ok=True)

    workdir = Path(tempfile.mkdtemp(prefix="code_run_", dir=session_dir.resolve()))

    # Files
    script_path = workdir / "script.py"
    runner_path = workdir / "runner.py"
    log_path = workdir / "stdout_stderr.txt"

    # Inject a safe runner that forces headless plots and auto-saves on plt.show()
    runner_src = textwrap.dedent("""
        import os, sys, glob, uuid, importlib
        from pathlib import Path
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        plt.rcParams["savefig.dpi"] = 100
        plt.rcParams["savefig.bbox"] = "tight"

        # Try optional libs; ignore if missing
        try:
            import pandas as pd
        except Exception:
            pd = None
        try:
            import numpy as np
        except Exception:
            np = None
        try:
            import seaborn as sns
        except Exception:
            sns = None
        try:
            import plotly, plotly.express as px, plotly.graph_objects as go
        except Exception:
            plotly = px = go = None

        # Replace plt.show() with a saver
        _orig_show = plt.show
        def _save_show(*args, **kwargs):
            fname = f"figure_{uuid.uuid4().hex}.png"
            try:
                plt.savefig(fname, dpi=100, bbox_inches="tight")
                print(f"[FIGURE_SAVED]{fname}")
            except Exception as e:
                print(f"[FIGURE_SAVE_ERROR]{e}")
        plt.show = _save_show

        code = open("script.py", "r", encoding="utf-8").read()
        # Build a minimal, explicit global namespace
        g = {"pd": pd, "np": np, "plt": plt, "sns": sns, "px": px, "go": go}
        exec(compile(code, "script.py", "exec"), g, None)
        
        # Detect if model saved its own figures (e.g., plt.savefig("..."))
        for png in Path(".").glob("*.png"):
            print(f"[FIGURE_SAVED]{png.name}")
    """)

        #     After exec, also sweep & save any open figures
        # for i in plt.get_fignums():
        #     fig = plt.figure(i)
                                 
        #     if fig._suptitle:
        #         title = fig._suptitle.get_text()
        #     elif fig.axes and fig.axes[0].get_title():
        #         title = fig.axes[0].get_title()
        #     else:
        #         title = None

        #     if title:
        #         # sanitize title to make it filesystem-safe
        #         safe_title = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in title)[:50]
        #         fname = f"figure_{safe_title}.png"
        #     else:
        #         fname = f"figure_{i}.png"

        #     try:
        #         fig.savefig(fname, dpi=100, bbox_inches="tight")
        #         print(f"[FIGURE_SAVED]{fname}")
        #     except Exception as e:
        #         print(f"[FIGURE_SAVE_ERROR]{e}")

    script_path.write_text(code, encoding="utf-8")
    runner_path.write_text(runner_src, encoding="utf-8")

    # Clean env (no proxies), headless
    env = os.environ.copy()
    for k in list(env.keys()):
        if k.upper().endswith("_PROXY") or k.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}:
            env.pop(k, None)
    env["MPLBACKEND"] = "Agg"

    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(runner_path),
        cwd=str(workdir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return [ToolResult(type=ToolResultType.text, content=f"Execution timed out after {timeout_sec}s." , error=True)]

    out = (stdout or b"").decode("utf-8", errors="ignore")
    err_txt = (stderr or b"").decode("utf-8", errors="ignore")

    # Collect any figures the runner reported
    images = []
    for line in out.splitlines():
        if line.startswith("[FIGURE_SAVED]"):
            fname = line.replace("[FIGURE_SAVED]", "").strip()
            fpath = workdir / fname
            if fpath.exists():
                images.append(str(fpath))
        # elif line.startswith("[CSV_SAVED]"):
        #     fname = line.replace("[CSV_SAVED]", "").strip()
        #     fpath = workdir / fname
        #     if fpath.exists():
        #         tables.append(str(fpath))

    if err_txt.strip():
        return [ToolResult(type=ToolResultType.text, content=f"Error during code execution:\n{err_txt}", error=True)]

    results: list[ToolResult] = []
    # Return images first (nice UX)
    for i, path in enumerate(images, 1):
        fname = os.path.basename(path)
        results.append(ToolResult(type=ToolResultType.image, content=path, desc=f"Generated figure {fname}"))

    

    # Then textual output (stdout + stderr)
    combined = out
    if err_txt.strip():
        combined += ("\n\n[stderr]\n" + err_txt)
    if combined.strip():
        # keep it manageable
        if len(combined) > 8000:
            combined = combined[:8000] + "\n...[truncated]"
        results.append(ToolResult(type=ToolResultType.text, content=combined))

    if not results:
        results.append(ToolResult(type=ToolResultType.text, content="No output produced."))

    print(f"Code run complete in {workdir}, results: {results}")
    return results
