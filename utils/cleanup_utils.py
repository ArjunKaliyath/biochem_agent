import shutil
from pathlib import Path
import logging, atexit
import chainlit as cl

logger = logging.getLogger(__name__)

@cl.on_chat_end
def cleanup_session():
    """Delete all temporary code_runner outputs for this session."""
    session_id = cl.user_session.get("id")
    if not session_id:
        return

    base_dir = Path(__file__).resolve().parent.parent 
    run_dir = base_dir / session_id
    if run_dir.exists():
        try:
            shutil.rmtree(run_dir)
            logger.info(f"[CLEANUP] Deleted {run_dir}")
        except Exception as e:
            logger.info(f"[CLEANUP ERROR] Could not delete {run_dir}: {e}")


#to cleanup files on unexpected exit
def cleanup_on_exit():
    # base_dir = Path("runs")
    base_dir = Path(__file__).resolve().parent.parent 
    base_dir = base_dir / "runs"
    if base_dir.exists():
        shutil.rmtree(base_dir)
        logger.info("Cleaned up temp directories on exit.")

atexit.register(cleanup_on_exit)
