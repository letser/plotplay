"""
Debug endpoint to fetch log files
"""
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

router = APIRouter()

LOGS_DIR = Path("logs")

@router.get("/logs/{session_id}")
async def get_session_log(session_id: str, since: int = Query(0)):
    """
    Fetches the log file for a given session.
    Can be used to poll for new log entries by providing the 'since'
    query parameter with the last known file size.
    """
    log_file = LOGS_DIR / f"session_{session_id}.log"

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found for this session.")

    with open(log_file, 'r', encoding='utf-8') as f:
        f.seek(since)
        content = f.read()
        current_size = f.tell()

    return {
        "content": content,
        "size": current_size
    }