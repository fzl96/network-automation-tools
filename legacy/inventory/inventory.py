import csv
import logging
import getpass
from napalm import get_network_driver
from cryptography.fernet import Fernet
from legacy.creds.credential_manager import load_credentials, save_credentials, load_key

INVENTORY_FILE = "inventory.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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


def detect_os_type(ip, username=None, password=None):
    drivers = ["ios", "junos", "nxos", "eos", "iosxr"]

    for driver_name in drivers:
        try:
            driver = get_network_driver(driver_name)
            device = driver(
                hostname=ip,
                username=username,
                password=password,
                optional_args={"timeout": 5},
            )
            device.open()
            facts = device.get_facts()
            device.close()

            hostname = facts.get("hostname", "Unknown")
            os_ver = facts.get("os_version", "Unknown")

            logging.info(f"Detected {os_ver} on {ip} ({driver_name}) - Hostname: {hostname}")
            return driver_name, hostname

        except Exception as e:
            msg = str(e).lower()
            if "auth" in msg or "password" in msg:
                return "AUTH_FAIL", None
            continue

    return "UNREACHABLE", None


def add_to_inventory(ip, hostname, os_type, username, password):
    enc_password = encrypt_value(password)
    rows = []
    found = False

    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            for row in reader:
                if len(row) < 5:
                    continue
                if row[1] == ip:
                    rows.append([hostname, ip, os_type, username, enc_password])
                    found = True
                else:
                    rows.append(row)
    except FileNotFoundError:
        pass

    if not found:
        rows.append([hostname, ip, os_type, username, enc_password])
        print(f"Added {hostname} ({ip}, {os_type})")
    else:
        print(f"Updated {hostname} ({ip}, {os_type})")

    with open(INVENTORY_FILE, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerows(rows)


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


def create_inventory(username=None, password=None):
    print("Create or Update Device Inventory")

    username, password = load_credentials()

    if not username or not password:
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")

        if input("Save credentials? (y/n): ").lower() == "y":
            save_credentials("default", username, password)

    auto_fix_inventory(username, password)

    while True:
        ip = input("Enter device IP (or 'done'): ").strip()
        if ip.lower() == "done":
            break

        os_type, hostname = detect_os_type(ip, username, password)

        if os_type == "AUTH_FAIL":
            print("Wrong credentials. Try again.")
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")
            os_type, hostname = detect_os_type(ip, username, password)

        if os_type and hostname:
            add_to_inventory(ip, hostname, os_type, username, password)
        else:
            print(f"Failed to detect OS for {ip}")

    print("Inventory saved.")


def show_inventory():
    print("\nCurrent Device Inventory")
    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            print(f"{'Hostname':<20} {'IP':<20} {'OS Type':<10} {'Username':<15} {'Password (encrypted)'}")
            print("-" * 80)

            for row in reader:
                if len(row) >= 5:
                    print(f"{row[0]:<20} {row[1]:<20} {row[2]:<10} {row[3]:<15} {row[4]}")
    except FileNotFoundError:
        print("Inventory not found.")

def load_devices(file="inventory.csv"):
    devices = []
    try:
        with open(file, "r") as f:
            reader = csv.reader(f, delimiter=";")

            for row in reader:
                if len(row) != 5:
                    continue

                hostname, ip, os_type, username, enc_password = row
                password = decrypt_value(enc_password)

                devices.append({
                    "hostname": hostname,
                    "ip": ip,
                    "os": os_type,
                    "username": username,
                    "password": password
                })

        return devices

    except FileNotFoundError:
        return []
