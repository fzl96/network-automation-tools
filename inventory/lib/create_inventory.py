#!/usr/bin/env python3
import csv
import getpass
from cryptography.fernet import Fernet
from inventory.lib.credential_manager import save_credentials, load_credentials, load_key
from inventory.lib.detect_os_type import detect_os_type

from rich.console import Console
from rich.prompt import Prompt
from rich import print as rprint

console = Console()


INVENTORY_FILE = "inventory.csv"

# ============================================================
# Encryption / Decryption Functions
# ============================================================

def encrypt_value(value):
    key = load_key()
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_value(value):
    key = load_key()
    f = Fernet(key)
    try:
        return f.decrypt(value.encode()).decode()
    except:
        return value



# ============================================================
# Main Logic Functions
# ============================================================
def create_inventory(username=None, password=None):
    console.print("[bold]\n📋 Create or Update Device Inventory[/bold]")
    console.rule(style="grey37")

    auto_fix_inventory(username, password)

    while True:
        ip = input("Enter device IP (or 'done'): ").strip()
        if ip.lower() == "done":
            break

        os_type, hostname = detect_os_type(ip, username, password)

        while os_type == "AUTH_FAIL":
            print("Wrong credentials. Try again.")
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")  # Secure password input
            os_type, hostname = detect_os_type(ip, username, password)
            
        if os_type and hostname:
            print(f"Authentication successful! IP: {ip}")
            add_to_inventory(ip, hostname, os_type, username, password)
        else:
            print(f"Failed to detect OS for {ip}")

    print("Inventory saved.")
    return username, password 

def auto_fix_inventory(username, password):
    print("Checking inventory for incomplete entries...")
    rows = []
    updated = False

    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            raw_lines = csvfile.readlines()
    except FileNotFoundError:
        print("No inventory to fix.")
        return

    for line in raw_lines:
        line = line.strip()
        if not line:
            continue

        if ";" not in line:
            ip = line
            os_type, hostname = detect_os_type(ip, username, password)

            if os_type == "AUTH_FAIL":
                print(f"Authentication failed for {ip}. Enter correct credentials:")
                u = input("Username: ").strip()
                p = getpass.getpass("Password: ")
                os_type, hostname = detect_os_type(ip, u, p)
                if os_type in ("AUTH_FAIL", "UNREACHABLE"):
                    rows.append(["Unknown", ip, "", "", ""])
                    continue
                rows.append([hostname, ip, os_type, u, encrypt_value(p)])
                updated = True
                continue

            rows.append([hostname or "Unknown", ip, os_type or "", username, encrypt_value(password)])
            updated = True
            continue

        parts = line.split(";")
        while len(parts) < 5:
            parts.append("")

        hostname, ip, os_type, row_user, row_pass = [p.strip() for p in parts]

        if row_pass and not row_pass.startswith("gAAAAA"):
            row_pass = encrypt_value(row_pass)

        if not hostname or not os_type:
            d_user = row_user or username
            d_pass = decrypt_value(row_pass) if row_pass else password

            os_new, hn_new = detect_os_type(ip, d_user, d_pass)

            if os_new == "AUTH_FAIL":
                print(f"Authentication failed for {ip}. Enter correct credentials:")
                u = input("Username: ").strip()
                p = getpass.getpass("Password: ")
                os_new, hn_new = detect_os_type(ip, u, p)
                if os_new in ("AUTH_FAIL", "UNREACHABLE"):
                    rows.append([hostname or "Unknown", ip, "", "", ""])
                    continue
                hostname = hn_new
                os_type = os_new
                row_user = u
                row_pass = encrypt_value(p)
                updated = True
            else:
                hostname = hn_new or hostname or "Unknown"
                os_type = os_new or os_type
                row_user = row_user or username
                row_pass = row_pass or encrypt_value(password)
                updated = True

        rows.append([hostname, ip, os_type, row_user, row_pass])

    with open(INVENTORY_FILE, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerows(rows)

    if updated:
        print("Inventory auto-updated.\n")
    else:
        print("Inventory is already complete.\n")

def add_to_inventory(ip, hostname, os_type, username, password):
    #  update entry di inventory.csv
    # Return "added" atau "updated" agar bisa dipakai GUI.
    enc_password = encrypt_value(password)
    rows = []
    found = False
    existing_ip_found = False

    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            for row in reader:
                if len(row) < 5:
                    continue
                if row[1] == ip:
                    rows.append([hostname, ip, os_type, username, enc_password])
                    found = True
                    existing_ip_found = True
                else:
                    rows.append(row)
    except FileNotFoundError:
        pass

    if existing_ip_found:
        print(f"⚠️ {ip} already exists in inventory. Skipping.")
        return "skipped"

    if not found:
        rows.append([hostname, ip, os_type, username, enc_password])
        print(f"Added {hostname} ({ip}, {os_type})")
        status = "added"
    else:
        print(f"Updated {hostname} ({ip}, {os_type})")
        status = "updated"

    with open(INVENTORY_FILE, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerows(rows)

    return status  
