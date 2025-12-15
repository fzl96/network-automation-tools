# inventory/lib/path.py
from inventory.lib.session_dir import get_session_dir
from pathlib import Path
import sys
import os
from pathlib import Path

def inventory_path() -> Path:
    session_dir = get_session_dir()
    inventory_file = session_dir / "inventory.csv"
    return inventory_file

def customer_path() -> Path:
    session_dir = get_session_dir()
    inventory_file = session_dir / "customer_config.json"
    return inventory_file

def get_app_dir():
    """Read-only app location"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

def get_data_dir(app_name="mantools"):
    """Writable per-user data directory (cross-platform)"""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        data_dir = base / app_name
    else:
        data_dir = Path.home() / f"{app_name}"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir