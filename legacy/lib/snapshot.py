import json
import os
from pathlib import Path
from legacy.lib.utils import (
    show_version,
    show_resources,
    show_interface,
    show_mac_address_table,
    show_ip_route,
    show_arp,
    show_logg,
)
from netmiko import (
    ConnectHandler,
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
)
from rich.console import Console
from datetime import datetime
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

console = Console()


def connect_to_device(creds):
    hostname = creds["hostname"]
    ip = creds["ip"]
    creds = {
        "device_type": creds["device_type"],
        "ip": creds["ip"],
        "username": creds["username"],
        "password": creds["password"],
        "secret": creds["password"],
        "fast_cli": False,
    }

    try:
        device = ConnectHandler(**creds)
        device.enable()
        return device

    except NetMikoTimeoutException:
        with open("connect_error.csv", "a") as file:
            file.write(f"{hostname};{ip};Device Unreachable/SSH not enabled")
        return None

    except NetMikoAuthenticationException:
        with open("connect_error.csv", "a") as file:
            file.write(f"{hostname};{ip};Authentication failure")
        return None


def capture_device_output(creds):
    hostname = creds["hostname"]
    device_type = creds["device_type"]

    conn = connect_to_device(creds)

    if conn:
        console.print(
            f"[bold cyan]Connected to {hostname} ({device_type})...[/bold cyan]"
        )

        # Collect raw data
        show_ver = show_version(conn, device_type)
        resources = show_resources(conn, device_type)
        interfaces = show_interface(conn, device_type)
        mac_address = show_mac_address_table(conn, device_type)
        ip_routes = show_ip_route(conn, device_type)
        arp_table = show_arp(conn, device_type)
        loggs = show_logg(conn, device_type)

        data = {
            "health_check": {
                "hostname": show_ver.get("hostname", ""),
                "uptime": show_ver.get("uptime", ""),
                "version": show_ver.get("version", ""),
                "cpu_utilization": resources.get("cpu_utilization", ""),
                "memory_utilization": resources.get("memory_utilization", ""),
                "storage_utilization": resources.get("storage_utilization", ""),
            },
            "interfaces": interfaces,
            "mac_address_table": mac_address,
            "routing_table": ip_routes,
            "arp_table": arp_table,
            "logs": loggs,
        }

        return data

    else:
        console.print(f"[red]ERROR: Failed to capture from {hostname}[/red]")


def health_check(filename, data, base_dir: str | None = None):
    if base_dir:
        path = os.path.join(base_dir, "legacy", "health_check")
    else:
        path = os.path.join("legacy", "results", "health_check")

    os.makedirs(path, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    health_check_path = os.path.join(path, f"health_check_{timestamp}.xlsx")

    wb: Workbook = Workbook()
    ws: Worksheet = wb.active  # type: ignore
    ws.title = "Health Check"

    # Header row
    headers = [
        "hostname",
        "version",
        "cpu_utilization",
        "memory_utilization",
        "storage_utilization",
        "uptime",
    ]
    ws.append(headers)

    # Fill rows per device
    for hostname, device_data in data.items():
        health = device_data.get("health_check", {})

        row = [
            health.get("hostname", hostname),
            health.get("version", ""),
            health.get("cpu_utilization", ""),
            health.get("memory_utilization", ""),
            health.get("storage_utilization", ""),
            health.get("uptime", ""),
        ]
        ws.append(row)

    # Optional: autosize columns a bit
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                val_len = len(str(cell.value)) if cell.value is not None else 0
                if val_len > max_len:
                    max_len = val_len
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = max_len + 2

    wb.save(health_check_path)

    print(f"Snapshot saved to {health_check_path}")


def take_snapshot(devices, base_dir: str | None = None):
    if base_dir:
        path = os.path.join(base_dir, "legacy", "snapshot")
    else:
        path = os.path.join("legacy", "results", "snapshot")

    os.makedirs(path, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    snapshot_path = os.path.join(path, f"snapshot_{timestamp}.json")

    result = {}
    for dev in devices:
        hostname = dev.get("hostname", "")
        data = capture_device_output(dev)
        result[hostname] = data

    with open(snapshot_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Snapshot saved to {snapshot_path}")

    health_check(f"health_check_{timestamp}.xlsx", result)
