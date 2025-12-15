# inventory/lib/path.py
from inventory.lib.session_dir import get_session_dir
from pathlib import Path

def inventory_path() -> Path:
    session_dir = get_session_dir()
    inventory_file = session_dir / "inventory.csv"
    return inventory_file
