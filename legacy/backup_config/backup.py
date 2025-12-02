#!/usr/bin/env python3
import os
import csv
import sys
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from legacy.inventory.inventory import detect_os_type

from napalm import get_network_driver
from rich.console import Console
from rich.table import Table

import paramiko

# === CONFIGURATION ===
INVENTORY_FILE = "inventory.csv"
BACKUP_DIR = "legacy/backup_config/output"

# === LOGGING SETUP ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === RICH CONSOLE ===
console = Console()


# === UTILITY FUNCTIONS ===
def ensure_dir(path: str) -> None:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def clear_screen() -> None:
    """Clear terminal screen for clean display."""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message: str = "\nPress ENTER to continue...") -> None:
    """Pause execution for user input."""
    input(message)


def slow_print(text: str, delay: float = 0.02) -> None:
    """Smooth typewriter-style output."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def load_inventory() -> List[Dict[str, str]]:
    devices = []
    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row:
                    continue

                # Split semicolon fields
                fields = row[0].split(";")
                fields += [""] * (5 - len(fields))

                name, ip, os_type, username, password = fields

                driver = row[1].strip() if len(row) > 1 else os_type

                devices.append({
                    "name": name,
                    "ip": ip,
                    "os": os_type,
                    "username": username,
                    "password": password,
                    "driver": driver
                })

    except FileNotFoundError:
        console.print("[yellow]⚠ Inventory file missing[/yellow]")

    return devices


# === DETECT OS FUNCTIONS ===
def detect_os(ip: str, username: str, password: str) -> str:
    """Detect OS and return napalm driver name."""
    try:
        # SSH banner detection
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password, timeout=5, look_for_keys=False)
        banner = client.get_transport().remote_version.lower()
        client.close()

        if "cisco" in banner:
            if "ios-xe" in banner or "iosxe" in banner:
                return "ios"
            if "nx-os" in banner or "nexus" in banner:
                return "nxos"
            if "asa" in banner:
                return "asa"

        if "juniper" in banner or "junos" in banner:
            return "junos"

        if "arista" in banner or "eos" in banner:
            return "eos"

    except Exception:
        pass  # Fall back to driver probing

    # NAPALM probe
    for drv in ["ios", "nxos", "asa", "junos", "eos"]:
        try:
            driver = get_network_driver(drv)
            conn = driver(hostname=ip, username=username, password=password)
            conn.open()
            conn.close()
            return drv
        except:
            continue

    return "ios"  # Default fallback

def auto_update_inventory(devices: List[Dict[str, str]], username: str, password: str) -> List[Dict[str, str]]:
    updated = []

    for dev in devices:
        ip = dev["ip"]
        user = dev["username"]
        pwd = dev["password"]

        console.print(f"[cyan]🔍 Detecting OS for {ip}...[/cyan]")

        os_type, hostname = detect_os_type(ip, user, pwd)

        if os_type in ("AUTH_FAIL", "UNREACHABLE"):
            console.print(f"[red]❌ OS detection failed for {ip} — keeping original[/red]")
            updated.append(dev)
            continue

        console.print(f"[green]✔ {ip} detected as {os_type}, hostname {hostname}[/green]")

        dev["os"] = os_type
        dev["hostname"] = hostname

        updated.append(dev)

    return updated

# === BACKUP FUNCTIONS ===
def backup_configs(device: Dict[str, str], username: str, password: str) -> None:
    """Backup configuration from a single device."""
    ip, driver_name = device["ip"], device["os"]

    try:
        logging.info(f"Connecting to {ip} using {driver_name} driver...")
        driver = get_network_driver(driver_name)
        device_conn = driver(hostname=ip, username=username, password=password)
        device_conn.open()

        facts = device_conn.get_facts()
        hostname = facts.get("hostname", ip)
        configs = device_conn.get_config()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        device_dir = os.path.join(BACKUP_DIR, hostname)
        ensure_dir(device_dir)

        for cfg_type, cfg_content in configs.items():
            if cfg_content:
                filename = os.path.join(device_dir, f"{hostname}_{cfg_type}_{timestamp}.cfg")
                with open(filename, "w") as f:
                    f.write(cfg_content) # type: ignore
                console.print(f"[green]✅ [{hostname}] Saved {cfg_type} config → {filename}[/green]")

        device_conn.close()
        logging.info(f"Backup completed for {ip}")

    except Exception as e:
        logging.error(f"Failed to back up {ip}: {e}")
        console.print(f"[red]❌ Error backing up {ip}: {e}[/red]")


def backup_commands(device: Dict[str, str], username: str, password: str, commands: List[str]) -> None:
    """Run and save specific command outputs for a device."""
    ip, driver_name = device["ip"], device["os"]

    try:
        logging.info(f"Connecting to {ip} for command execution...")
        driver = get_network_driver(driver_name)
        device_conn = driver(hostname=ip, username=username, password=password)
        device_conn.open()

        facts = device_conn.get_facts()
        hostname = facts.get("hostname", ip)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        device_dir = os.path.join(BACKUP_DIR, hostname)
        ensure_dir(device_dir)

        output_filename = os.path.join(device_dir, f"{hostname}_{timestamp}.txt")

        with open(output_filename, "w") as f:
            f.write(f"### Command Backup for {hostname} ({ip}) ###\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 60 + "\n\n")

            for cmd in commands:
                logging.info(f"Running command on {hostname}: {cmd}")
                output = device_conn.cli([cmd])[cmd]
                f.write(f"$ {cmd}\n{output}\n{'-' * 60}\n\n")

        console.print(f"[cyan]📄 [{hostname}] Command outputs saved to: {output_filename}[/cyan]")

        device_conn.close()
        logging.info(f"Command backup completed for {hostname}")

    except Exception as e:
        logging.error(f"Failed to execute command on {ip}: {e}")
        console.print(f"[red]❌ Error executing command on {ip}: {e}[/red]")


# === UI FUNCTIONS ===
def print_header() -> None:
    clear_screen()
    print("=" * 60)
    print("🧩  BACKUP CONFIG TOOLS".center(60))
    print("=" * 60)
    print()


def print_menu() -> None:
    print("MAIN MENU")
    print("-" * 50)
    print("1. Backup configurations")
    print("2. Backup specific command outputs")
    print("3. Both (configs + commands)")
    print("q. Exit Program")
    print("-" * 50)


def display_inventory_table(devices: List[Dict[str, str]]) -> None:
    table = Table(title="Detected Devices")
    table.add_column("IP Address", style="cyan")
    table.add_column("OS / Driver", style="magenta")
    for dev in devices:
        table.add_row(dev["ip"], dev["os"])
    console.print(table)


# === MAIN LOGIC ===
def run_backup(username: Optional[str] = None, password: Optional[str] = None) -> None:
    """Main function to handle user menu and backup options."""
    devices = load_inventory()
    devices = auto_update_inventory(devices, username, password)

    if not devices:
        console.print("[yellow]⚠️ No devices found in inventory. Please create an inventory first.[/yellow]")
        return

    if not username:
        username = input("Enter username for backup: ").strip()
    if not password:
        password = input("Enter password: ").strip()

    while True:
        print_header()
        print_menu()
        display_inventory_table(devices)

        choice = input("\nEnter your choice: ").strip().lower()

        if choice == "1":
            slow_print("\n🚀 Starting configuration backups...\n")
            for dev in devices:
                backup_configs(dev, username, password)
            pause()    

        elif choice == "2":
            raw_cmds = input("Enter command(s) separated by commas (e.g., 'show version,show interfaces'): ").strip()
            commands = [cmd.strip() for cmd in raw_cmds.split(",") if cmd.strip()]
            slow_print("\n🚀 Starting command backups...\n")
            for dev in devices:
                backup_commands(dev, username, password, commands)
            pause()    

        elif choice == "3":
            raw_cmds = input("Enter command(s) separated by commas (e.g., 'show version,show interfaces'): ").strip()
            commands = [cmd.strip() for cmd in raw_cmds.split(",") if cmd.strip()]
            slow_print("\n🚀 Starting full backups (config + commands)...\n")
            for dev in devices:
                backup_commands(dev, username, password, commands)
                backup_configs(dev, username, password)
            pause()    

        elif choice == "q":
            slow_print("\nExiting backup system...")
            print("✅ Backup system exit complete. Goodbye! 👋")
            break

        else:
            console.print("[yellow]⚠️ Invalid choice, please try again.[/yellow]")
            pause()


if __name__ == "__main__":
    run_backup()
