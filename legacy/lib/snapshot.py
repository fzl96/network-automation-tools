import copy
import json
import os
from legacy.lib.utils import (
    load_devices,
    show_version,
    show_resources,
    show_interface,
    show_mac_address_table,
    show_ip_route,
    show_arp,
    show_logg,
    connect_to_device,
)
from rich.console import Console
from datetime import datetime
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment
from legacy.customer_context import get_customer_name

console = Console()


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
        interfaces = show_interface(conn)
        mac_address = show_mac_address_table(conn)
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


def autosize_columns(ws: Worksheet) -> None:
    """Autosize all columns in a worksheet based on content length."""
    for col in ws.columns:
        first_cell = col[0]
        if first_cell.column is None:
            continue

        col_letter = get_column_letter(first_cell.column)
        max_len = 0

        for cell in col:
            try:
                val = "" if cell.value is None else str(cell.value)
                if len(val) > max_len:
                    max_len = len(val)
            except Exception:
                pass

        ws.column_dimensions[col_letter].width = max_len + 2


def health_check(customer_name, data, base_dir):
    path = os.path.join(base_dir, "health_check")
    os.makedirs(path, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    health_check_path = os.path.join(
        path, f"{customer_name}_health_check_{timestamp}.xlsx"
    )

    wb: Workbook = Workbook()

    ws_health: Worksheet = wb.create_sheet("Health Check", 0)

    headers_health = [
        "Hostname",
        "Version",
        "Cpu utilization",
        "Memory utilization",
        "Storage utilization",
        "Uptime",
    ]
    ws_health.append(headers_health)

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
        ws_health.append(row)

    autosize_columns(ws_health)

    ws_crc: Worksheet = wb.create_sheet("CRC Interfaces", 1)

    headers_crc = [
        "Hostname",
        "Interface",
        "CRC",
        "Link status",
        "Protocol status",
        "Description",
    ]
    ws_crc.append(headers_crc)

    current_row = 2

    for hostname, device_data in data.items():
        interfaces = device_data.get("interfaces", [])

        first_row_for_host = None
        rows_for_this_host = 0

        for intf in interfaces:
            crc_raw = intf.get("crc", "")
            crc = "" if crc_raw is None else str(crc_raw).strip()

            if crc in ("", "0"):
                continue

            ws_crc.append(
                [
                    hostname,
                    intf.get("interface", ""),
                    crc,
                    intf.get("link_status", ""),
                    intf.get("protocol_status", ""),
                    intf.get("description", ""),
                ]
            )

            if first_row_for_host is None:
                first_row_for_host = current_row

            current_row += 1
            rows_for_this_host += 1

        if first_row_for_host is not None and rows_for_this_host > 1:
            ws_crc.merge_cells(
                start_row=first_row_for_host,
                start_column=1,
                end_row=first_row_for_host + rows_for_this_host - 1,
                end_column=1,
            )

            master_cell = ws_crc.cell(first_row_for_host, 1)
            master_cell.value = hostname

            master_cell.alignment = Alignment(vertical="center")

            autosize_columns(ws_crc)

            if "Sheet" in wb.sheetnames:
                std = wb["Sheet"]
                if std.max_row == 1 and std["A1"].value is None:
                    wb.remove(std)

    wb.save(health_check_path)
    print(f"Snapshot saved to {health_check_path}")


def take_snapshot(base_dir=None):
    customer_name = get_customer_name()
    devices = load_devices()

    if base_dir:
        path = os.path.join(base_dir, customer_name, "legacy")
    else:
        path = os.path.join("results", customer_name, "legacy")

    os.makedirs(path, exist_ok=True)

    snapshot_dir = os.path.join(path, "snapshot")
    os.makedirs(snapshot_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot_path = os.path.join(
        snapshot_dir, f"{customer_name}_snapshot_{timestamp}.json"
    )

    result = {}
    for dev in devices:
        hostname = dev.get("hostname", "")
        data = capture_device_output(dev)
        result[hostname] = data

    with open(snapshot_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Snapshot saved to {snapshot_path}")

    health_check(customer_name, result, path)
