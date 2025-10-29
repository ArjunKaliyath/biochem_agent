import json
import shutil
from pathlib import Path
import pandas as pd
import base64


# ----------------- CSV Summaries -----------------
CSV_SAMPLE_ROWS = 6
CSV_MAX_COLS_LIST = 24  # Max columns to list in summary

def summarize_csv_for_prompt(file_path: str,
                             sample_rows: int = 6,
                             max_cols_list: int = 24,
                             top_n_values: int = 5) -> str:
    """
    Produce a concise yet information-dense summary of a CSV for LLM prompting.
    Includes schema, descriptive stats, value distributions, and a JSON preview.
    """
    p = Path(file_path)
    size_kb = round(p.stat().st_size / 1024, 1)
    summary_lines = [
        f"[CSV SUMMARY]",
        f"Path: {p.resolve()}",
        f"Name: {p.name}",
        f"Size: {size_kb} KB",
    ]

    try:
        # Load small sample + infer types
        df = pd.read_csv(file_path, nrows=2000)  # read max 2000 rows for summary
    except Exception as e:
        return "\n".join(summary_lines + [f"Error reading CSV: {e}"])

    nrows, ncols = df.shape
    summary_lines.append(f"Approx. shape: {nrows}×{ncols}")
    cols = list(df.columns)
    if ncols > max_cols_list:
        summary_lines.append(f"(Showing first {max_cols_list} of {ncols} columns)")
        cols = cols[:max_cols_list]

    # Schema with dtypes and nulls
    schema_lines = ["\n[SCHEMA]"]
    for c in cols:
        dtype = str(df[c].dtype)
        nulls = int(df[c].isna().sum())
        uniq = df[c].nunique(dropna=True)
        schema_lines.append(f"- {c} ({dtype}) — {nulls} nulls, {uniq} unique")

    # Value summaries
    val_lines = ["\n[VALUE INSIGHTS]"]
    for c in cols:
        s = df[c]
        dtype = str(s.dtype)
        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe(percentiles=[]).to_dict()
            stats = ", ".join([f"{k}={round(v,3)}" for k, v in desc.items() if k in ["min","mean","max"]])
            val_lines.append(f"- {c}: {stats}")
        else:
            # categorical / string
            vc = s.dropna().astype(str).value_counts()
            if len(vc) == 0:
                val_lines.append(f"- {c}: all null")
            elif len(vc) <= top_n_values:
                vals = list(vc.index[:top_n_values])
                val_lines.append(f"- {c}: limited unique values {vals}")
            else:
                top_vals = list(vc.index[:top_n_values])
                val_lines.append(f"- {c}: top {top_n_values} = {top_vals}, appears categorical or identifier")

    # JSON preview (sample rows)
    preview_json = df.head(sample_rows).to_dict(orient="records")
    summary_lines += schema_lines + val_lines + [
        "\n[PREVIEW JSON]",
        json.dumps(preview_json, indent=2, ensure_ascii=False)[:3000],  # safe truncate
        "\nGuidance: The model should use this summary to infer data meaning, "
        "read the real CSV from the path when writing code (via pandas.read_csv)."
    ]
    return "\n".join(summary_lines)


def prepare_file_for_api(file_el):
    """
    Prepare Chainlit file element for Responses API.
    - CSV/TSV: summarized via summarize_csv_for_prompt()
    - TXT/JSON: short textual preview
    - Images: base64-encoded
    - Other: path info only
    """
    p = Path(file_el.path)

    original_name = file_el.name or p.name
    new_path = p.parent / original_name

    if not new_path.exists():
        shutil.copy(p, new_path)
    else: #if path already exists
        # Avoid collisions by appending small suffix
        stem, ext = Path(original_name).stem, Path(original_name).suffix
        new_path = p.parent / f"{stem}_copy{ext}"
        shutil.copy(p, new_path)

    ext = p.suffix.lower()
    print('file path',p)
    print('new path',new_path)
    print('file ext',ext)

    # CSV / TSV -> full data summary
    if ext in [".csv", ".tsv"]:
        try:
            summary = summarize_csv_for_prompt(str(new_path))
        except Exception as e:
            summary = f"[CSV SUMMARY ERROR]\nPath: {new_path.resolve()}\nError: {e}"
        return [{
            "type": "input_text",
            "text": summary
        }], None


    #Image files -> base64 encode
    if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"]:
        with open(new_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        mime = "image/" + ("jpeg" if ext in [".jpg", ".jpeg"] else ext.lstrip("."))

        return [
        {"type": "input_text",
         "text": f"[IMAGE FILE] {new_path.name}: user-uploaded image for pathway visualization or analysis."},
        {"type": "input_image", "image_url": f"data:{mime};base64,{data}"}
        ], None

    #Fallback: just show path
    return [{
        "type": "input_text",
        "text": (
            f"[FILE INFO]\n"
            f"Path: {new_path.resolve()}\n"
            f"Name: {new_path.name}\n"
            f"Size: {round(new_path.stat().st_size/1024,1)} KB\n"
            f"Note: Unsupported preview type for this model."
        ),
    }], None