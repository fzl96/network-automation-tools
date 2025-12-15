# inventory/lib/session_dir.py
from pathlib import Path
import tempfile

_SESSION_DIR = Path(tempfile.mkdtemp(prefix="mantools_"))
_SESSION_DIR.mkdir(parents=True, exist_ok=True)

def get_session_dir() -> Path:
    return _SESSION_DIR