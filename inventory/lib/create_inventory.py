#!/usr/bin/env python3
import csv
import getpass
from cryptography.fernet import Fernet
from inventory.lib.credential_manager import save_credentials, load_credentials, load_key
from inventory.lib.detect_os_type import detect_os_type

from rich.console import Console
from pathlib import Path
import sys

console = Console()

from inventory.lib.path import inventory_path

INVENTORY_FILE = inventory_path()

# ============================================================
# Encryption / Decryption Functions
# ============================================================

def encrypt_value(value):
    """Encrypt a string value."""
    if not value:
        return ""
    key = load_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(value):
    """Decrypt a string value."""
    if not value or not value.strip():
        return ""
    key = load_key()
    f = Fernet(key)
    try:
        return f.decrypt(value.encode()).decode()
    except:
        # If decryption fails, return original value (might be plaintext)
        return value

# ============================================================
# Main Logic Functions
# ============================================================

def create_inventory(username=None, password=None):
    """Create or update device inventory with OS detection."""
    console.print("[bold]\n📋 Create or Update Device Inventory[/bold]")
    console.rule(style="grey37")


    # First, try to fix any existing incomplete entries
    auto_fix_inventory(username, password)

    # Get credentials if not provided
    if not username or not password:
        username, password = get_credentials_from_user()

    while True:
        ip = input("Enter device IP (or 'done'): ").strip()
        if ip.lower() == "done":
            break

        # Validate IP format (basic check)
        if not is_valid_ip(ip):
            console.print(f"[red]Invalid IP address format: {ip}[/red]")
            continue

        os_type, hostname = detect_os_type(ip, username, password)

        # Handle authentication failures
        while os_type == "AUTH_FAIL":
            console.print("[red]Authentication failed. Please enter correct credentials:[/red]")
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")
            os_type, hostname = detect_os_type(ip, username, password)
            
        # Handle unreachable devices
        if os_type == "UNREACHABLE":
            console.print(f"[yellow]Device {ip} is unreachable. Skipping...[/yellow]")
            if console.input("Add anyway with manual details? (y/N): ").lower() == 'y':
                hostname = input(f"Enter hostname for {ip}: ").strip() or "Unknown"
                os_type = input(f"Enter OS type for {ip}: ").strip() or "UNKNOWN"
                add_to_inventory(ip, hostname, os_type, username, password)
            continue
        
        # Handle unknown SSH devices
        if os_type == "UNKNOWN_SSH":
            console.print(f"[yellow]Device {ip} responds to SSH but OS type is unknown[/yellow]")
            hostname = input(f"Enter hostname for {ip}: ").strip() or f"device-{ip}"
            os_type = "UNKNOWN_SSH"
            add_to_inventory(ip, hostname, os_type, username, password)
            continue

        if os_type and hostname:
            console.print(f"[green]✓ Detected: {hostname} ({os_type}) at {ip}[/green]")
            add_to_inventory(ip, hostname, os_type, username, password)
        else:
            console.print(f"[red]Failed to detect OS for {ip}[/red]")
            if console.input("Add with manual details? (y/N): ").lower() == 'y':
                hostname = input(f"Enter hostname for {ip}: ").strip() or "Unknown"
                os_type = input(f"Enter OS type for {ip}: ").strip() or "UNKNOWN"
                add_to_inventory(ip, hostname, os_type, username, password)

    console.print("[green]✓ Inventory saved.[/green]")
    return username, password

def auto_fix_inventory(username=None, password=None):
    """Automatically fix incomplete inventory entries."""
    console.print("Checking inventory for incomplete entries...")
    
    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            rows = list(reader)
    except FileNotFoundError:
        console.print("[yellow]No inventory file found.[/yellow]")
        return
    except Exception as e:
        console.print(f"[red]Error reading inventory: {e}[/red]")
        return

    if not rows:
        console.print("[yellow]Inventory is empty.[/yellow]")
        return

    updated = False
    updated_rows = []

    for i, row in enumerate(rows):
        # Ensure row has exactly 5 columns
        while len(row) < 5:
            row.append("")
        
        hostname, ip, os_type, row_user, row_pass = [cell.strip() for cell in row[:5]]
        
        # Skip empty rows or headers
        if not ip or ip.lower() == "ip" or ip.lower() == "hostname":
            updated_rows.append(row)
            continue

        # Get credentials for detection
        current_user = row_user or username
        current_pass = decrypt_value(row_pass) if row_pass else password
        
        # If no credentials available, skip
        if not current_user or not current_pass:
            console.print(f"[yellow]Skipping {ip}: No credentials available[/yellow]")
            updated_rows.append([hostname or "Unknown", ip, os_type or "", row_user, row_pass])
            continue

        assert current_user is not None
        assert current_pass is not None

        # Check if we need to detect OS/hostname
        needs_detection = not hostname or not os_type or hostname == "Unknown" or os_type in ["", "UNKNOWN"]
        
        if needs_detection:
            console.print(f"Detecting OS for {ip}...")
            os_new, hn_new = detect_os_type(ip, current_user, current_pass)
            
            if os_new == "AUTH_FAIL":
                console.print(f"[red]Authentication failed for {ip}[/red]")
                # Try to get new credentials
                console.print("Please enter correct credentials:")
                new_user = input(f"Username for {ip}: ").strip()
                new_pass = getpass.getpass(f"Password for {ip}: ")
                
                os_new, hn_new = detect_os_type(ip, new_user, new_pass)
                
                if os_new in ("AUTH_FAIL", "UNREACHABLE"):
                    updated_rows.append([hostname or "Unknown", ip, "", new_user, encrypt_value(new_pass)])
                else:
                    updated_rows.append([hn_new or "Unknown", ip, os_new, new_user, encrypt_value(new_pass)])
                    updated = True
            elif os_new == "UNREACHABLE":
                console.print(f"[yellow]Device {ip} is unreachable[/yellow]")
                updated_rows.append([hostname or "Unknown", ip, os_type or "UNREACHABLE", row_user, row_pass])
            else:
                # Update with detected values
                hostname = hn_new or hostname or "Unknown"
                os_type = os_new or os_type
                updated_rows.append([hostname, ip, os_type, row_user, row_pass])
                updated = True
        else:
            # Keep existing row
            updated_rows.append([hostname, ip, os_type, row_user, row_pass])

    # Write updated inventory
    if updated:
        try:
            with open(INVENTORY_FILE, "w", newline="") as csvfile:
                writer = csv.writer(csvfile, delimiter=";")
                writer.writerows(updated_rows)
            console.print("[green]✓ Inventory auto-updated.[/green]\n")
        except Exception as e:
            console.print(f"[red]Error saving inventory: {e}[/red]")
    else:
        console.print("[green]✓ Inventory is already complete.[/green]\n")

def add_to_inventory(ip, hostname, os_type, username, password):
    """Add or update a device in the inventory."""
    status = "unknown"
    enc_password = encrypt_value(password) if password else ""
    
    # Read existing inventory
    existing_ips = set()
    rows = []
    
    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            for row in reader:
                if len(row) >= 2 and row[1]:  # Check if row has at least IP
                    existing_ips.add(row[1].strip())
                    rows.append(row)
    except FileNotFoundError:
        pass  # File doesn't exist yet
    
    # Check if IP already exists
    if ip in existing_ips:
        # Update existing entry
        for i, row in enumerate(rows):
            if len(row) >= 2 and row[1] == ip:
                old_hostname = row[0] if len(row) > 0 else "Unknown"
                rows[i] = [hostname, ip, os_type, username, enc_password]
                console.print(f"⚠️ Updated existing entry: {old_hostname} → {hostname} ({ip})")
                status = "updated"
                break
    else:
        # Add new entry
        rows.append([hostname, ip, os_type, username, enc_password])
        console.print(f"[green]✓ Added {hostname} ({ip}, {os_type})[/green]")
        status = "added"
    
    # Write back to file
    try:
        with open(INVENTORY_FILE, "w", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter=";")
            writer.writerows(rows)
    except Exception as e:
        console.print(f"[red]Error saving to inventory: {e}[/red]")
        status = "error"
    
    return status

def get_credentials_from_user():
    """Prompt user for credentials if not provided."""
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ")
    return username, password

def is_valid_ip(ip):
    """Basic IP address validation."""
    import socket
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        # Check if it's a hostname
        try:
            socket.gethostbyname(ip)
            return True
        except socket.error:
            return False

# Helper function for command-line usage
if __name__ == "__main__":
    # Initialize credentials from credential manager if available
    try:
        stored_username, stored_password = load_credentials()
        if stored_username and stored_password:
            console.print("[green]Using stored credentials[/green]")
            username, password = create_inventory(stored_username, stored_password)
        else:
            username, password = create_inventory()
    except Exception as e:
        console.print(f"[red]Error loading credentials: {e}[/red]")
        username, password = create_inventory()
    
    # Optionally save credentials for future use
    if username and password:
        save = console.input("\nSave these credentials for future use? (y/N): ").lower()
        if save == 'y':
            save_credentials("default", username, password)
            console.print("[green]Credentials saved.[/green]")