#!/usr/bin/env python3
import os
import csv
import sys
import time
import logging
import shutil
import pyfiglet
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from cryptography.fernet import Fernet
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
    SSHException
)

from legacy.customer_context import get_customer_name
from inventory.lib.credential_manager import load_key

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# CONSTANTS & INITIAL SETUP
KEY_FILE = os.path.join("inventory/lib", "key.key")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

console = Console()

GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"

# Netmiko device type mapping for backup operations
DEVICE_TYPE_MAP = {
    'cisco_ios': 'cisco_ios',
    'cisco_nxos': 'cisco_nxos',
    'cisco_xe': 'cisco_ios',
    'cisco_xr': 'cisco_xr',
    'cisco_asa': 'cisco_asa',
    'generic': 'generic',
}

# Device-specific configuration commands
CONFIG_COMMANDS = {
    'cisco_ios': ['show running-config'],
    'cisco_nxos': ['show running-config'],
    'cisco_xr': ['show running-config'],
    'cisco_asa': ['show running-config'],
    'cisco_xe': ['show running-config'],
    'generic': ['show running-config'],
}


# === UTILITY FUNCTIONS ===
def ensure_dir(path: str) -> None:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def clear_screen() -> None:
    """Clear terminal screen for clean display."""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\nPress ENTER to continue..."):
    green = "\033[32m"  # Green
    reset = "\033[0m"
    input(f"{green}{message}{reset}")


def slow_print(text: str, delay: float = 0.02) -> None:
    """Smooth typewriter-style output."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def get_terminal_width(default=100):
    """Return current terminal width or a default if detection fails"""
    try:
        width = shutil.get_terminal_size().columns
        return width
    except:
        return default

def decrypt_password(enc_password: str) -> str:
    """Decrypt password using Fernet."""
    if not enc_password or not enc_password.strip():
        return ""
    
    try:
        key = load_key()
        fernet = Fernet(key)
        return fernet.decrypt(enc_password.encode()).decode()
    except Exception:
        # If decryption fails, assume it's already plaintext
        return enc_password

# INVENTORY FUNCTIONS
def load_inventory(file="inventory.csv"):
    devices = []
    try:
        with open(file, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            for row in reader:
                if len(row) != 5:
                    continue

                hostname, ip, os_type, username, password = row
                
                # Skip empty rows or headers
                if not ip or ip.lower() == "ip" or ip.lower() == "hostname":
                    continue

                # Skip APIC devices if not supported in backup
                if "apic" in os_type.lower():
                    console.print(f"[yellow]⚠ Skipping APIC device {ip} - not supported in backup[/yellow]")
                    continue

                devices.append({
                    "hostname": hostname or "Unknown",
                    "ip": ip,
                    "os": os_type,
                    "username": username,
                    "password": password,
                })

    except FileNotFoundError:
        console.print("[yellow]⚠ Inventory file missing[/yellow]")
    except Exception as e:
        console.print(f"[red]Error loading inventory: {e}[/red]")

    return devices

def connect_with_netmiko(device: Dict[str, str]) -> ConnectHandler:
    """Connect to device using Netmiko."""
    ip = device["ip"]
    os_type = device["os"]
    username = device.get("username", "")
    password = device.get("password", "")
    
    # Decrypt password
    password = decrypt_password(password)
    
    if not username or not password:
        raise ValueError(f"Missing username/password for {ip}")
    
    # Map OS type to Netmiko device type
    device_type = DEVICE_TYPE_MAP.get(os_type, 'generic')
    
    # Device connection parameters
    device_params = {
        'device_type': device_type,
        'host': ip,
        'username': username,
        'password': password,
        'timeout': 15,
        'session_timeout': 30,
        'banner_timeout': 15,
        'global_delay_factor': 1,
    }
    
    # Device-specific adjustments
    if device_type in ['cisco_ios', 'cisco_xe', 'cisco_asa']:
        device_params['secret'] = password  # Enable mode password
    elif device_type == 'juniper_junos':
        device_params['port'] = 22  # SSH port
    elif device_type == 'arista_eos':
        device_params['global_delay_factor'] = 2  # Arista needs more delay
    
    try:
        connection = ConnectHandler(**device_params)
        return connection
    except NetmikoAuthenticationException:
        raise RuntimeError(f"Authentication failed for {ip}")
    except NetmikoTimeoutException:
        raise RuntimeError(f"Connection timeout for {ip}")
    except SSHException as e:
        raise RuntimeError(f"SSH error for {ip}: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to {ip}: {str(e)}")



# === BACKUP FUNCTIONS ===
def backup_configs(device: Dict[str, str], device_dir: str) -> None:
    """Backup device configuration using Netmiko."""
    customer = get_customer_name()
    ip = device["ip"]
    os_type = device["os"]
    hostname = device.get("hostname")

    try:
        connection = connect_with_netmiko(device)
        device_type = DEVICE_TYPE_MAP.get(os_type, 'generic')
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        
        # Get configuration commands for this device type
        config_cmds = CONFIG_COMMANDS.get(device_type, ['show running-config'])
        
        for cmd in config_cmds:
            try:
                console.print(f"[cyan]📝 Running: {cmd} on {hostname}[/cyan]")
                data = connection.send_command(
                    cmd, 
                    expect_string=r'#|\$|>',
                    read_timeout=30,
                    delay_factor=2
                )
                
                # Create a simple filename
                filename = f"{customer}_{hostname}_command_{timestamp}.txt"
                filepath = os.path.join(device_dir, filename)
                
                # Write to file
                with open(filepath, "w") as f:
                    f.write(f"# {hostname} | {customer} | {timestamp}\n\n")
                    f.write(data)
                
                logging.info(f"Backed up {cmd} for {hostname} to {filename}")
                console.print(f"[green]✓ [{hostname}] Config saved: {os.path.basename(filename)}[/green]")
                
            except Exception as e:
                logging.error(f"Failed to execute {cmd} on {hostname}: {e}")
                console.print(f"[yellow]⚠ Failed to execute {cmd} on {hostname}: {str(e)[:100]}[/yellow]")
        
        connection.disconnect()
        logging.info(f"Backup completed for {hostname}")
                
    except Exception as e:
        logging.error(f"Failed to back up {ip}: {e}")
        console.print(f"[red]❌ Error backing up {ip}: {e}[/red]")

def backup_commands(device: Dict[str, str], commands: List[str], device_dir: str) -> None:
    """Execute custom commands and save output."""
    customer = get_customer_name()
    ip = device["ip"]
    hostname = device.get("hostname")
    os_type = device["os"]

    try:
        connection = connect_with_netmiko(device)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        
        output_filename = os.path.join(
            device_dir, f"{customer}_{hostname}_commands_{timestamp}.txt"
        )

        with open(output_filename, "w") as f:
            f.write(f"### Command Backup for {hostname} ({ip}) ###\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"OS Type: {os_type}\n")
            f.write("=" * 60 + "\n\n")

            for cmd in commands:
                try:
                    console.print(f"[cyan]📝 Running: {cmd} on {hostname}[/cyan]")
                    output = connection.send_command(
                        cmd, 
                        expect_string=r'#|\$|>',
                        read_timeout=30,
                        delay_factor=2
                    )
                    f.write(f"$ {cmd}\n{output}\n{'-' * 60}\n\n")
                    logging.info(f"Executed {cmd} on {hostname}")
                except Exception as e:
                    error_msg = f"ERROR executing '{cmd}': {str(e)[:100]}"
                    f.write(f"$ {cmd}\n{error_msg}\n{'-' * 60}\n\n")
                    logging.error(f"Failed to execute {cmd} on {hostname}: {e}")
                    console.print(f"[yellow]⚠ Failed: {cmd} on {hostname}[/yellow]")

        console.print(f"[green]✓ [{hostname}] Command outputs saved to: {os.path.basename(output_filename)}[/green]")

        connection.disconnect()
        logging.info(f"Command backup completed for {hostname}")

    except Exception as e:
        logging.error(f"Failed to execute commands on {ip}: {e}")
        console.print(f"[red]❌ Error executing commands on {ip}: {e}[/red]")

# === UI FUNCTIONS ===
def print_header():
    """Display header with colored logo and big title"""
    clear_screen()
    width = get_terminal_width()
    red = "\033[31m"
    reset = "\033[0m"

    print()  # spacing

    ascii_title = pyfiglet.figlet_format("BACKUP CONFIG TOOLS", font="standard")

    for line in ascii_title.splitlines():
        print(f"{red}{line.center(width)}{reset}")

    print()  # spacing

def print_menu() -> None:
    console.print("\n")
    menu_text = """
        [bold]1.[/bold] Backup configurations

        [bold]2.[/bold] Both (configs + commands)

        [bold]q.[/bold] Exit
        """
    console.print(
        Panel(
            menu_text,
            title="[bold]🧰 Backup Options[/bold]",
            title_align="left",
            border_style="grey37",
            padding=(1, 2),
        )
    )    

# === MAIN LOGIC ===
def run_backup(base_dir= None):
    
    """Main function to handle user menu and backup options."""
    devices = load_inventory()
    customer = get_customer_name()

    if not devices:
        console.print(
            "[yellow]⚠️ No devices found in inventory. Please create an inventory first.[/yellow]"
        )
        return

    # Get Directory for backups
    if base_dir:
        path = os.path.join(base_dir, customer, "legacy", "backup")
    else:
        path = os.path.join("results", customer, "legacy", "backup")
    os.makedirs(path, exist_ok=True)

    while True:
        print_header()
        print_menu()
        green = "\033[32m"
        reset = "\033[0m"        

        choice = input("\nEnter your choice: ").strip().lower()

        if choice == "1":
            slow_print(f"{green}\n⏳ Starting configuration backups...{reset}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:        
                for dev in devices:
                    hostname = dev.get("hostname")
                    if (
                        not dev.get("ip")
                        or not dev.get("username")
                        or not dev.get("password")
                        or not dev.get("os")
                    ):
                        console.print(f"[yellow]⚠️ Device {hostname} entry is incomplete, skipping[/yellow]")
                        continue

                    task = progress.add_task(f"Backing up {hostname}...", start=False)
                    progress.start_task(task)

                    device_dir = os.path.join(path, hostname)
                    ensure_dir(device_dir)
                    backup_configs(dev, device_dir)
                
                    progress.update(task, completed=1)
                    logging.info(f"Completed backup for {hostname} save in {device_dir}")

            print(f"{GREEN} ✅ All configuration backups completed.{RESET}")        
            pause()

        elif choice == "2":
            raw_cmds = input(
                "Enter command(s) separated by commas (e.g., 'show version,show interfaces'): "
            ).strip()
            commands = [cmd.strip() for cmd in raw_cmds.split(",") if cmd.strip()]
            
            if not commands:
                console.print("[red]❌ No commands provided, skipping[/red]")
                pause()
                continue
                
            slow_print(f"{green}\n⏳ Starting configuration and command backups...{reset}")
            
            # Get Directory for backups
            if base_dir:
                path = os.path.join(base_dir, customer, "legacy", "backup")
            else:
                path = os.path.join("results", customer, "legacy", "backup")
            os.makedirs(path, exist_ok=True)
            
            # Log the backup directory path
            logging.info(f"Backup path: {path}")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                             
                for dev in devices:
                    hostname = dev.get("hostname", dev.get("name", ""))
                    if (
                        not dev.get("ip")
                        or not dev.get("username")
                        or not dev.get("password")
                        or not dev.get("os")
                    ):
                        console.print(f"[yellow]⚠️ Device {hostname} entry is incomplete, skipping[/yellow]")
                        continue
                    
                    task = progress.add_task(f"Backing up {hostname}...", start=False)
                    progress.start_task(task)

                    device_dir = os.path.join(path, hostname)
                    ensure_dir(device_dir)
                    
                    # Backup both configs and custom commands
                    backup_configs(dev, device_dir)
                    backup_commands(dev, commands, device_dir)
                    
                    progress.update(task, completed=2)
                    
            pause()

        elif choice == "q":
            slow_print(f"{green}\nExit backup tools...{reset}")
            time.sleep(0.3)
            console.print("✅ Goodbye! 👋")
            break

        else:
            console.print("[yellow]⚠️ Invalid choice, please try again.[/yellow]")
            pause()

if __name__ == "__main__":
    run_backup()