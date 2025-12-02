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
    # First, try APIC detection
    apic_result = quick_apic_check(ip, username, password)
    if apic_result:
        return apic_result
    
    # Try drivers in optimal order for Cisco devices
    drivers = ["ios", "nxos_ssh", "nxos", "iosxr", "junos", "eos"]
    
    for driver_name in drivers:
        try:
            logging.debug(f"Trying driver: {driver_name} for {ip}")
            optional_args = {
                "timeout": 10,
                "banner_timeout": 15,
                "session_timeout": 20
            }
            
            # Special handling for NX-OS SSH
            if driver_name == "nxos_ssh":
                result = try_nxos_ssh(ip, username, password)
                if result:
                    return result
                continue
            
            driver = get_network_driver(driver_name)
            
            # Platform-specific optional arguments
            optional_args = {"timeout": 5}
            
            if driver_name == "nxos":
                # NX-OS with Netconf
                optional_args.update({
                    "port": 22,
                    "transport": "ssh",
                    "allow_agent": False,
                    "hostkey_verify": False
                })
            elif driver_name == "iosxr":
                # IOS-XR with Netconf
                optional_args.update({
                    "port": 22,
                    "transport": "ssh",
                    "hostkey_verify": False
                })
            elif driver_name == "junos":
                # JunOS typically uses port 830 for Netconf
                optional_args.update({"port": 830})
            elif driver_name == "eos":
                # EOS uses eAPI/HTTP
                optional_args.update({"port": 443, "transport": "https"})
            
            device = driver(
                hostname=ip,
                username=username,
                password=password,
                optional_args=optional_args,
            )
            
            device.open()
            facts = device.get_facts()
            device.close()

            hostname = facts.get("hostname", "Unknown")
            os_ver = facts.get("os_version", "Unknown")

            logging.info(f"Detected {os_ver} on {ip} ({driver_name}) - Hostname: {hostname}")
            return driver_name, hostname

        except Exception as e:
            error_msg = str(e).lower()
            logging.debug(f"Driver {driver_name} failed for {ip}: {str(e)[:200]}")
            
            if "auth" in error_msg or "password" in error_msg or "authentication" in error_msg:
                return "AUTH_FAIL", None
            elif "connection refused" in error_msg or "channel closed" in error_msg:
                # Try next driver
                continue
            elif "not found" in error_msg or "no driver" in error_msg:
                # Driver name might not exist (like nxos_ssh)
                continue
            else:
                continue

    return "UNREACHABLE", None


def quick_apic_check(ip, username, password):
    """Simple APIC detection without risky hostname extraction"""
    try:
        import paramiko
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        client.connect(
            hostname=ip,
            username=username,
            password=password,
            port=22,
            timeout=5,
            banner_timeout=8,
        )
        
        transport = client.get_transport()
        if transport:
            banner = transport.get_banner()
            # Check for APIC banner (from your logs)
            if banner and "Application Policy Infrastructure Controller" in str(banner):
                logging.info(f"Detected APIC banner on {ip}")
                client.close()
                # Use a safe default hostname
                return "apic", "apic-controller"
        
        client.close()
        return None
        
    except paramiko.ssh_exception.AuthenticationException:
        return "AUTH_FAIL", None
    except Exception:
        return None


def try_nxos_ssh(ip, username, password):
    """Try NX-OS using SSH (not Netconf)"""
    try:
        # Try using netmiko for SSH-based NX-OS detection
        from netmiko import ConnectHandler
        
        device = {
            'device_type': 'cisco_nxos',
            'host': ip,
            'username': username,
            'password': password,
            'timeout': 5,
            'global_delay_factor': 1,
        }
        
        connection = ConnectHandler(**device)
        
        # Get basic info
        output = connection.send_command("show version", use_textfsm=True)
        
        if isinstance(output, list) and len(output) > 0:
            # TextFSM parsed output
            hostname = output[0].get('hostname', 'Unknown')
            os_version = output[0].get('os', 'Unknown')
        else:
            # Raw output
            hostname = "nxos-switch"
            os_version = "NX-OS"
            # Try to get hostname
            hostname_output = connection.send_command("show hostname")
            if hostname_output:
                hostname = hostname_output.strip()
        
        connection.disconnect()
        logging.info(f"Detected NX-OS via SSH on {ip} - Hostname: {hostname}")
        return "nxos", hostname
        
    except Exception as e:
        logging.debug(f"NX-OS SSH detection failed for {ip}: {str(e)[:100]}")
        return None


# Alternative: Simplified version focusing on your error
def detect_os_type_simple(ip, username=None, password=None):
    """Simplified detection focusing on NX-OS and APIC"""
    
    # Check APIC first
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=username, password=password, timeout=5)
        banner = client.get_transport().get_banner() if client.get_transport() else ""
        if "Application Policy Infrastructure Controller" in str(banner):
            return "apic", "apic-controller"
        client.close()
    except:
        pass
    
    # Try NX-OS with SSH (not eAPI)
    drivers_to_try = [
        ("nxos", {"port": 22, "transport": "ssh", "hostkey_verify": False}),
        ("ios", {}),
        ("iosxr", {"port": 22, "transport": "ssh", "hostkey_verify": False}),
    ]
    
    for driver_name, extra_args in drivers_to_try:
        try:
            driver = get_network_driver(driver_name)
            optional_args = {"timeout": 5}
            optional_args.update(extra_args)
            
            device = driver(
                hostname=ip,
                username=username,
                password=password,
                optional_args=optional_args,
            )
            device.open()
            facts = device.get_facts()
            device.close()
            
            hostname = facts.get("hostname", "Unknown")
            logging.info(f"Detected {driver_name.upper()} on {ip} - Hostname: {hostname}")
            return driver_name, hostname
            
        except Exception as e:
            error_msg = str(e).lower()
            if "auth" in error_msg:
                return "AUTH_FAIL", None
            continue
    
    return "UNREACHABLE", None


# If you're getting JSON errors, the device might be NX-OS but Napalm is trying wrong method
def detect_nxos_fallback(ip, username, password):
    """Fallback method for NX-OS detection"""
    try:
        # Method 1: Try with netmiko directly
        from netmiko import ConnectHandler
        
        for device_type in ['cisco_nxos', 'cisco_ios', 'cisco_xr']:
            try:
                device = {
                    'device_type': device_type,
                    'host': ip,
                    'username': username,
                    'password': password,
                    'timeout': 5,
                }
                
                conn = ConnectHandler(**device)
                prompt = conn.find_prompt()
                conn.disconnect()
                
                if device_type == 'cisco_nxos':
                    return "nxos", prompt.strip('#').strip()
                elif device_type == 'cisco_ios':
                    return "ios", prompt.strip('#').strip()
                elif device_type == 'cisco_xr':
                    return "iosxr", prompt.strip('#').strip()
                    
            except:
                continue
                
    except Exception as e:
        logging.debug(f"Fallback detection failed: {e}")
    
    return None

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
