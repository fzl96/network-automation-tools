# ✅ Updated snapshotter.py to include timestamped filenames and history viewer with interactive snapshot comparison

import re
import json
import os
import datetime
from aci.api.aci_client import (
    get_drop_errors,
    get_epgs,
    get_endpoints_with_ip,
    get_fabric_health,
    get_faults,
    get_interface_status,
    get_output_errors,
    get_urib_routes,
    get_interface_errors,
    get_crc_errors,
    get_output_path_ep,
    get_pc_aggr,
)
from aci.lib.utils import load_devices, apic_login
from rich.console import Console
from legacy.customer_context import get_customer_name

console = Console()



PATH_RE = re.compile(
    r"topology/pod-(?P<pod>\d+)/paths-(?P<node>\d+)/pathep-\[(?P<if>[^\]]+)\]"
)


def parse_path_from_attr(fabric_path_dn: str):
    if not fabric_path_dn:
        return "", ""
    m = PATH_RE.search(fabric_path_dn)
    if not m:
        return "", fabric_path_dn

    return m.group("node"), m.group("if")


def process_endpoints(cookies, apic_ip):
    endpoints = []
    endpoints_with_ip = get_endpoints_with_ip(cookies, apic_ip)
    epgs = get_epgs(cookies, apic_ip)

    epg_map = {}
    for epg in epgs:
        fvAEPg = epg.get("fvAEPg", {})
        attr = fvAEPg.get("attributes", {})
        dn = attr.get("dn", "")
        descr = attr.get("descr", "")
        if dn:
            epg_map[dn] = descr

    for ep in endpoints_with_ip:
        cep = ep.get("fvCEp", {})
        attr = cep.get("attributes", {})
        dn = attr.get("dn", "") or ""
        mac = attr.get("mac", "")
        encap = attr.get("encap", "") or ""
        fabric_path_dn = attr.get("fabricPathDn", "")

        node, iface = parse_path_from_attr(fabric_path_dn)

        ips = []
        for ch in cep.get("children", []):
            if "fvIp" in ch:
                ip = ch["fvIp"]["attributes"].get("addr")
                ips.append(ip if ip else "")

        if not ips:
            ips = [""]

        epg_dn = dn.split("/cep-")[0] if "/cep-" in dn else ""
        epg_descr = epg_map.get(epg_dn, "")

        for ip in ips:
            data = {
                "node": node,
                "interface": iface,
                "mac": mac,
                "ip": ip,
                "vlan": encap,
                "dn": dn,
                "epg_descr": epg_descr,
            }
            endpoints.append(data)

    return endpoints


def take_snapshot(cookies, apic_ip):
    # Collect all data
    data = {
        "fabric_health": get_fabric_health(cookies, apic_ip),
        "faults": get_faults(cookies, apic_ip),
        "interfaces": get_interface_status(cookies, apic_ip),
        "interface_errors": get_interface_errors(cookies, apic_ip),
        "drop_errors": get_drop_errors(cookies, apic_ip),
        "output_errors": get_output_errors(cookies, apic_ip),
        "crc_errors": get_crc_errors(cookies, apic_ip),
        "endpoints": process_endpoints(cookies, apic_ip),
        "urib_routes": get_urib_routes(cookies, apic_ip),
        "path_ep": get_output_path_ep(cookies, apic_ip),
        "pc_aggr": get_pc_aggr(cookies, apic_ip),
    }

    return data


def list_snapshots(base_dir=None):
    customer = get_customer_name()
    if base_dir:
        folder = os.path.join(base_dir, customer, "aci", "snapshot")
    else:
        folder = os.path.join("results", customer, "aci", "snapshot")

    if not os.path.exists(folder):
        print("📂 No snapshots taken yet.")
        return []
    files = [f for f in os.listdir(folder) if f.endswith(".json")]
    if not files:
        print("📂 No snapshot files found.")
        return []
    files.sort()
    print("\n🕓 Available Snapshots:")
    for i, f in enumerate(files):
        print(f"  [{i + 1}] {f}")
    return files


def choose_snapshots(base_dir=None):
    customer = get_customer_name()
    files = list_snapshots(base_dir)
    if base_dir:
        folder = os.path.join(base_dir, customer, "aci", "snapshot")
    else:
        folder = os.path.join("results", customer, "aci", "snapshot")

    if len(files) < 2:
        print("❌ Need at least 2 snapshots to compare.")
        return None, None
    try:
        first = int(input("🔢 Enter number for FIRST snapshot: ")) - 1
        second = int(input("🔢 Enter number for SECOND snapshot: ")) - 1
        if 0 <= first < len(files) and 0 <= second < len(files):
            return os.path.join(folder, files[first]), os.path.join(
                folder, files[second]
            )
        else:
            print("❌ Invalid selection.")
            return None, None
    except ValueError:
        print("❌ Please enter valid numbers.")
        return None, None


def take_all_snapshots(base_dir=None):
    customer = get_customer_name()
    devices = load_devices()

    combined = {}

    for device in devices:
        hostname = device.get("hostname", "")
        apic_ip = device.get("ip", "")
        username = device.get("username")
        password = device.get("password", "")

        if not username or not password or not apic_ip:
            console.print(
                f"[red]Skipping {hostname}: credentials not found in .env[/red]"
            )

        console.rule(f"[bold blue]{hostname} ({apic_ip})[/bold blue]", style="grey37")

        cookies = apic_login(apic_ip, username, password)

        if not cookies:
            console.print(f"[red]Skipping {hostname}: login failed[/red]")
            continue

        data = take_snapshot(cookies, apic_ip)
        combined[hostname] = data

    # Create directory structure
    if base_dir:
        snapshot_dir = os.path.join(base_dir, customer, "aci", "snapshot")
    else:
        snapshot_dir = os.path.join("results", customer, "aci", "snapshot")

    os.makedirs(snapshot_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M")
    filename = f"{customer}_snapshot_{timestamp}.json"
    filepath = os.path.join(snapshot_dir, filename)
    with open(filepath, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"✅ Snapshot saved to {filepath}")
