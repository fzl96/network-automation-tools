import os
import csv
import requests
from typing import Optional
from requests.cookies import RequestsCookieJar
from cryptography.fernet import Fernet
from inventory.lib.credential_manager import load_key
from rich.console import Console
console = Console()

from inventory.lib.path import inventory_path
def load_devices(file=None):
    file = inventory_path() if file is None else file
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

        console.print(f"[green]✓ Successfully authenticated to APIC {apic_ip}[/green]")
        return resp.cookies

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to APIC at {apic_ip}")
    except requests.exceptions.Timeout:
        print("✗ Connection timeout.")
    except Exception as e:
        print(f"✗ Login failed: {str(e)}")

from rich.table import Table
from rich.console import Console

console = Console()

def print_general_table(apic, result):
    table = Table(
        title=f"{apic} - General",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Category", style="magenta")
    table.add_column("Item", style="cyan")
    table.add_column("Details", style="yellow")

    fh = result.get("fabric_health", {})
    table.add_row("Fabric Health", "Before", str(fh.get("before", "N/A")))
    table.add_row("Fabric Health", "After", str(fh.get("after", "N/A")))

    for fault in result.get("new_faults", []):
        table.add_row("New Faults", str(fault), "")

    for fault in result.get("cleared_faults", []):
        table.add_row("Cleared Faults", str(fault), "")

    intf_changes = result.get("interface_changes", {}) or {}

    for change in intf_changes.get("status_changed", []):
        table.add_row("Interface Status Changed", change, "")

    for intf in intf_changes.get("missing", []):
        table.add_row("Interface Missing", intf, "")

    for intf in intf_changes.get("new", []):
        table.add_row("Interface New", intf, "")

    iec = result.get("interface_error_changes", {}) or {}
    if isinstance(iec, dict):
        for k, v in iec.items():
            table.add_row("Interface Error Changes", str(k), str(v))
    elif isinstance(iec, list):
        for row in iec:
            dn = row.get("dn") or f"{row.get('node','')}/{row.get('interface','')}"
            table.add_row(
                "Interface Error Changes",
                dn,
                f"{row.get('before','')} -> {row.get('after','')}",
            )

    urib = result.get("urib_route_changes", {}) or {}
    for route in urib.get("missing", []):
        table.add_row("URIB Routes Missing", route, "")

    for route in urib.get("new", []):
        table.add_row("URIB Routes New", route, "")

    console.print(table)

def print_interface_errors_table(apic, result):
    table = Table(
        title=f"{apic} - Interface Errors",
        show_header=True,
        header_style="bold cyan",
    )

    headers = [
        "Category",
        "Node",
        "Interface",
        "Description",
        "Before",
        "After",
        "Mac",
        "IP",
        "VLAN",
        "Description",
    ]

    for h in headers:
        table.add_column(h)

    def add_rows(category, rows):
        for row in rows or []:
            table.add_row(
                category,
                str(row.get("node", "")),
                str(row.get("interface", "")),
                str(row.get("descr", "")),
                str(row.get("before", "")),
                str(row.get("after", "")),
                str(row.get("mac", "")),
                str(row.get("ip", "")),
                str(row.get("vlan", "")),
                str(row.get("epg_descr", "")),
            )

    add_rows("CRC Changes", result.get("crc_error_changes", []))
    add_rows("Drop Changes", result.get("drop_error_changes", []))
    add_rows("Output Error Changes", result.get("output_error_changes", []))

    console.print(table)

def print_endpoints_table(apic, result):
    table = Table(
        title=f"{apic} - Endpoints",
        show_header=True,
        header_style="bold cyan",
    )

    headers = [
        "Category",
        "Endpoint",
        "Mac",
        "IP address",
        "Switch",
        "Interface",
        "VLAN",
        "Description",
    ]

    for h in headers:
        table.add_column(h)

    for cat, key in (
        ("New Endpoints", "new_endpoints"),
        ("Missing Endpoints", "missing_endpoints"),
    ):
        for ep in result.get(key, []) or []:
            if not isinstance(ep, dict):
                continue
            table.add_row(
                cat,
                ep.get("dn", ""),
                ep.get("mac", ""),
                ep.get("ip", ""),
                ep.get("node", ""),
                ep.get("interface", ""),
                ep.get("vlan", ""),
                ep.get("epg_descr", ""),
            )

    console.print(table)

