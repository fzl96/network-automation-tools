import sys
import os
import csv
import requests
from typing import Optional
from requests.cookies import RequestsCookieJar
from cryptography.fernet import Fernet
from legacy.lib.utils import load_key


def load_devices(file="inventory.csv"):
    devices = []
    try:
        with open(file, "r") as f:
            reader = csv.reader(f, delimiter=";")

            for row in reader:
                if len(row) != 5:
                    continue

                hostname, ip, os_type, username, enc_password = row

                if "apic" not in os_type:
                    continue

                devices.append(
                    {
                        "hostname": hostname,
                        "ip": ip,
                        "os": os_type,
                        "username": username,
                        "password": enc_password,
                    }
                )

        return devices

    except FileNotFoundError:
        return []


def apic_login(
    apic_ip: str, username: str, password: str
) -> Optional[RequestsCookieJar]:
    key = load_key()
    fernet = Fernet(key)

    login_url = f"https://{apic_ip}/api/aaaLogin.json"
    auth_payload = {
        "aaaUser": {
            "attributes": {
                "name": username,
                "pwd": fernet.decrypt(password.encode()).decode(),
            }
        }
    }

    try:
        resp = requests.post(login_url, json=auth_payload, verify=False, timeout=30)
        if resp.status_code != 200:
            print(f"✗ Login failed with status code: {resp.status_code}")
            return None

        data = resp.json()
        if "imdata" in data and len(data["imdata"]) > 0:
            if isinstance(data["imdata"][0], dict) and "error" in data["imdata"][0]:
                print("✗ Authentication failed: Invalid credentials.")
                return None

        print(f"✓ Successfully authenticated to APIC {apic_ip}")
        return resp.cookies

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to APIC at {apic_ip}")
    except requests.exceptions.Timeout:
        print("✗ Connection timeout.")
    except Exception as e:
        print(f"✗ Login failed: {str(e)}")


def get_key_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
