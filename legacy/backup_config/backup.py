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

# === INVENTORY LOADING FUNCTION ===
from inventory.lib.path import inventory_path
def load_inventory(file=None):
    file = inventory_path() if file is None else file
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
                
                # Standardize OS type to lowercase
                os_type = os_type.lower().strip()

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

# === NETMIKO CONNECTION & BACKUP HELPERS ===
def disable_paging(connection, device_type: str) -> None:
    """Disable paging on the device."""
    disable_commands = []
    
    # Common paging disable commands
    if device_type in ['cisco_ios', 'cisco_xe', 'cisco_asa']:
        disable_commands = ["terminal length 0", "terminal width 511"]
    elif device_type == 'cisco_nxos':
        disable_commands = ["terminal length 0", "terminal width 511"]
    elif device_type == 'cisco_xr':
        disable_commands = ["terminal length 0", "terminal width 300"]
    else:
        disable_commands = ["terminal length 0"]  # Default

    console.print(f"[yellow]⚙  Sending paging commands: {disable_commands}[/yellow]")    
    
    for cmd in disable_commands:
        try:
            connection.send_command_timing(cmd, delay_factor=2)
            time.sleep(1)
            console.print(f"[green]✓ Sent: {cmd}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Failed '{cmd}': {e}[/yellow]")
            logging.debug(f"Failed to run '{cmd}': {e}")
    # Send an extra return to clear any prompts
    try:
        connection.write_channel("\n")
        time.sleep(0.5)
    except:
        pass            

def connect_with_netmiko(device: Dict[str, str]):
    """Connect to device using Netmiko."""
    ip = device["ip"]
    device_type = device["os"].lower()
    username = device.get("username", "")
    password = device.get("password", "")
    
    # Decrypt password
    password = decrypt_password(password)
    
    if not username or not password:
        raise ValueError(f"Missing username/password for {ip}")
    
    # Optimized connection parameters
    device_params = {
        'device_type': device_type,
        'host': ip,
        'username': username,
        'password': password,
        'timeout': 30,
        'session_timeout': 60,
        'banner_timeout': 15,
        'global_delay_factor': 2,
        'fast_cli': False,  # Disable for reliability
    }
    
    # Platform-specific adjustments
    if device_type in ['cisco_ios', 'cisco_xe', 'cisco_asa']:
        device_params['secret'] = password  # Enable password
        device_params['global_cmd_verify'] = False
    
    try:
        connection = ConnectHandler(**device_params)
        return connection
    except Exception as e:
        raise RuntimeError(f"Failed to connect to {ip}: {str(e)}")
    
# === BACKUP FUNCTIONS ===
def backup_configs(device: Dict[str, str], device_dir: str) -> None:
    """Backup device configuration using Netmiko - Simplified version."""
    customer = get_customer_name()
    ip = device["ip"]
    device_type = device["os"].lower()
    hostname = device.get("hostname")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"{customer}_{hostname}_{timestamp}.txt"
    filepath = os.path.join(device_dir, filename)
    
    console.print(f"[cyan]📡 Backing up {hostname} ({ip}) as {device_type}...[/cyan]")
    
    try:
        # Connect to device
        connection = connect_with_netmiko(device)
        
        # CRITICAL: Disable paging - this is often the main issue
        console.print(f"[yellow]📄 Disabling paging...[/yellow]")
        disable_paging(connection, device_type)
        
        # Wait a moment for paging to take effect
        time.sleep(2)
        
        # Get the running config
        console.print(f"[yellow]📥 Retrieving configuration...[/yellow]")
        
        config_output = get_full_running_config(connection)
        
        # Save to file
        header = f"Backup created: {timestamp}\n"
        header += f"Device: {hostname} ({ip})\n"
        header += f"Device Type: {device_type}\n"
        header += f"Output Length: {len(config_output)} characters\n"
        header += "=" * 60 + "\n\n"
        
        with open(filepath, "w", encoding='utf-8') as f:
            f.write(header)
            f.write(config_output)
        
        file_size = os.path.getsize(filepath)
        console.print(f"[green]✅ [{hostname}] Backup saved: {filename} ({file_size} bytes)[/green]")
        logging.info(f"Successfully backed up {hostname} ({ip}) to {filepath}")
        connection.disconnect()
        
    except Exception as e:
        console.print(f"[red]❌ Error backing up {hostname}: {e}[/red]")
        logging.error(f"Failed to back up {hostname}: {e}")
        
        # Save error message
        with open(filepath, "w") as f:
            f.write(f"ERROR backing up {hostname} ({ip}):\n{str(e)}\n")

def get_full_running_config(connection) -> str:
    try:
        # Clear the channel buffer first
        connection.clear_buffer()
        
        # Send the command
        connection.write_channel("show running-config\n")
        time.sleep(5)  # Initial wait
        
        output = ""
        max_wait_time = 60  # Maximum total wait time
        start_time = time.time()
        last_data_time = start_time
        
        # Keep reading until no more data for 3 seconds or max time reached
        while time.time() - start_time < max_wait_time:
            time.sleep(2)
            chunk = connection.read_channel()
            
            if chunk:
                output += chunk
                last_data_time = time.time()
                console.print(f"[yellow]📥 Received {len(chunk)} chars, total: {len(output)}[/yellow]")
            else:
                # No data received, check if we should continue waiting
                if time.time() - last_data_time > 3:  # No data for 3 seconds
                    console.print("[yellow]📭 No more data, stopping...[/yellow]")
                    break
        
        console.print(f"[green]✓ Collected {len(output)} characters[/green]")
        
        # Try to send a return to get any remaining buffered output
        try:
            connection.write_channel("\n")
            time.sleep(2)
            final_chunk = connection.read_channel()
            if final_chunk:
                output += final_chunk
                console.print(f"[yellow]📥 Final chunk: {len(final_chunk)} chars[/yellow]")
        except:
            pass
        
        # Clean up the output - remove any remaining prompts
        lines = output.split('\n')
        clean_lines = []
        for line in lines:
            # Skip lines that are just prompts or empty
            if line.strip() and not (line.endswith('#') or line.endswith('>') or line.endswith('$')):
                # Also skip common command echo
                if not line.startswith('show running-config'):
                    clean_lines.append(line)
        
        clean_output = '\n'.join(clean_lines)
        console.print(f"[green]✓ Cleaned output: {len(clean_output)} characters[/green]")
        
        return clean_output
        
    except Exception as e:
        console.print(f"[yellow]⚠ Alternative method also failed: {e}[/yellow]")
        return ""

def backup_commands(device: Dict[str, str], commands: List[str], device_dir: str) -> None:
    """Execute custom commands and save output."""
    customer = get_customer_name()
    ip = device["ip"]
    hostname = device.get("hostname")
    device_type = device["os"].lower()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"{customer}_{hostname}_commands_{timestamp}.txt"
    filepath = os.path.join(device_dir, filename)
    
    connection = None
    try:
        connection = connect_with_netmiko(device)
        
        # Disable paging
        disable_paging(connection, device_type)
        connection.clear_buffer()
        
        with open(filepath, "w", encoding='utf-8') as f:
            # Write header
            f.write(f"Command backup: {timestamp}\n")
            f.write(f"Device: {hostname} ({ip})\n")
            f.write(f"Type: {device_type}\n")
            f.write("=" * 60 + "\n\n")
            
            for cmd in commands:
                try:
                    output = connection.send_command(
                        cmd,
                        expect_string=None,
                        read_timeout=300,
                        delay_factor=3
                    )
                    f.write(f"$ {cmd}\n{output}\n{'-' * 60}\n\n")
                    console.print(f"[green]✓ {cmd} on {hostname}[/green]")
                except Exception as e:
                    error_msg = f"ERROR: {str(e)[:100]}"
                    f.write(f"$ {cmd}\n{error_msg}\n{'-' * 60}\n\n")
                    console.print(f"[yellow]⚠ {cmd} failed on {hostname}[/yellow]")
        
        file_size = os.path.getsize(filepath)
        console.print(f"[green]✅ Commands saved: {filename} ({file_size} bytes)[/green]")
                
    except Exception as e:
        console.print(f"[red]❌ Error on {hostname}: {e}[/red]")
    finally:
        if connection:
            connection.disconnect()        

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