from pathlib import Path

def inventory_path():
    base = Path.home() / ".mantools"
    base.mkdir(exist_ok=True)
    return base / "inventory.csv"
