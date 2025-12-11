#!/usr/bin/env python3
import logging
from napalm import get_network_driver
from paramiko import AuthenticationException


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def detect_os_type(ip, username=None, password=None):
    # First, try APIC detection
    apic_result = quick_apic_check(ip, username, password)
    if apic_result:
        return apic_result
    
    # Try drivers in optimal order for Cisco devices
    drivers = ["ios", "nxos_ssh", "nxos", "iosxr","junos","eos"]
    
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
            optional_args: dict[str, int | str | bool] = {"timeout": 5}
            
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


            if driver_name == "ios" and os_ver == "Unknown":
                logging.debug(f"IOS driver returned unknown OS version on {ip}, trying next driver")
                continue

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
    """Detect APIC by parsing 'show versions' and extracting controller hostname."""
    try:
        import paramiko

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=ip,
            username=username,
            password=password,
            timeout=8,
            banner_timeout=8,
            auth_timeout=8
        )

        # Menggunakan cmd 'show versions' (format tabel Role/Pod/Node/Name/Version)
        stdin, stdout, stderr = client.exec_command("show versions", timeout=5)
        output = stdout.read().decode("utf-8", errors="ignore")

        client.close()

        hostname = None

        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            
            low = stripped.lower()
            if low.startswith("role"):
                continue
            if all(ch in "- " for ch in stripped):
                continue

            parts = stripped.split()
            
            if len(parts) < 5:
                continue

            role = parts[0].lower()
            if role != "controller":
                continue

            
            name_tokens = parts[3:-1]
            if name_tokens:
                hostname = " ".join(name_tokens)
            else:
                hostname = parts[3]

            logging.info(
                f"Detected APIC via 'show versions' on {ip} - Hostname: {hostname}"
            )
            return "apic", hostname

        # Fallback: if tabel format has keyword APIC
        lowered = output.lower()
        if any(keyword in lowered for keyword in [
            "cisco apic",
            "application policy infrastructure controller",
            "aci fabric",
            "aci version"
        ]):
            logging.info(f"Detected APIC CLI output (fallback) on {ip}")
            return "apic", "apic-controller"

        return None

    except AuthenticationException:
        return "AUTH_FAIL", None
    except Exception as e:
        logging.debug(f"APIC check error on {ip}: {e}")
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