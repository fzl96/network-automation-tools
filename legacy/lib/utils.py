import sys
import json
import csv
import os
import re
from datetime import datetime
import time
from netmiko import (
    ConnectHandler,
    NetMikoTimeoutException,
    NetMikoAuthenticationException,
)
from netmiko.base_connection import BaseConnection
from rich.console import Console
from cryptography.fernet import Fernet
from typing import Dict, List, Any, cast
from legacy.customer_context import get_customer_name

KEY_FILE = os.path.join("legacy/creds", "key.key")

console = Console()


def load_key():
    key_path = get_key_path(os.path.join("legacy", "creds", "key.key"))
    with open(key_path, "rb") as key_file:
        return key_file.read()


def map_os_to_device_type(os_type: str) -> str:
    os_type = os_type.lower()

    mapping = {
        "ios": "cisco_ios",
        "iosxe": "cisco_ios",
        "nxos_ssh": "cisco_nxos",
        "nxos": "cisco_nxos",
        "eos": "arista_eos",
        "junos": "juniper_junos",
        "iosxr": "cisco_xr",
    }

    return mapping.get(os_type, "cisco_ios")  # safe default


def connect_to_device(creds):
    key = load_key()
    fernet = Fernet(key)
    hostname = creds["hostname"]
    ip = creds["ip"]

    creds = {
        "device_type": creds["device_type"],
        "ip": creds["ip"],
        "username": creds["username"],
        "password": fernet.decrypt(creds["password"].encode()).decode(),
        "secret": fernet.decrypt(creds["password"].encode()).decode(),
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


def show_version(conn: BaseConnection, device_type: str):
    data = {}
    try:
        show_ver = conn.send_command("show version", use_textfsm=True)
        if isinstance(show_ver, str) or isinstance(show_ver, dict):
            return {}
        first = show_ver[0]
        hostname = first.get("hostname", "")
        uptime = first.get("uptime", "")
        version = first.get("version", "") or first.get("os", "")

        data = {
            "hostname": hostname,
            "uptime": uptime,
            "version": version,
        }

        return data
    except Exception as e:
        print(f"Errors: {e}")
        return {}


def show_resources(conn: BaseConnection, device_type: str):
    try:
        cpu_util = "0%"
        mem_util = "0%"
        storage_util = "0%"

        if "nxos" not in device_type:
            # Be explicit for the type-checker
            proc_cpu = conn.send_command("show proc cpu")
            proc_mem = conn.send_command("show proc mem sort")
            sh_dir_output = conn.send_command("dir | sec free")

            # env_fan = conn.send_command("show environment fan")
            # env_power = conn.send_command("show environment power", use_textfsm=True)
            # print(env_power)

            # CPU
            r_cpu = re.search(r"\s+five minutes:\s(\d+)%", str(proc_cpu))
            if r_cpu:
                cpu_util = f"{r_cpu.group(1)}%"

            # MEMORY
            r_mem = re.search(
                r"Processor Pool Total:\s+(\d+)\s+Used:\s+(\d+)", str(proc_mem)
            )
            if r_mem:
                total_ram = int(r_mem.group(1))
                used_ram = int(r_mem.group(2))
                if total_ram > 0:
                    mem_perc = (used_ram / total_ram) * 100
                    mem_util = f"{mem_perc:.2f}%"

            # STORAGE
            r_dir = re.search(
                r"(\d+)\s+bytes\s+total\s+\((\d+)\s+bytes\s+free\)",
                str(sh_dir_output),
            )
            if r_dir:
                total_storage_bytes = int(r_dir.group(1))
                free_storage_bytes = int(r_dir.group(2))
                if total_storage_bytes > 0:
                    used_storage_bytes = total_storage_bytes - free_storage_bytes
                    storage_perc = (used_storage_bytes / total_storage_bytes) * 100
                    storage_util = f"{storage_perc:.2f}%"

            return {
                "cpu_utilization": cpu_util,
                "memory_utilization": mem_util,
                "storage_utilization": storage_util,
            }

        # NXOS
        system_resources = str(conn.send_command("show system resources"))
        dir_output = str(conn.send_command("dir | in bytes"))

        ## CPU
        r_cpu = re.search(
            r"CPU\s+states\s+:\s+([\d.]+)%\s+user,\s+([\d.]+)%\s+kernel",
            system_resources,
        )
        if r_cpu:
            cpu_util = f"{float(r_cpu.group(1)) + float(r_cpu.group(2)):.2f}%"

        ## MEMORY
        r_mem = re.search(
            r"Memory usage:\s+(\d+)K\s+total,\s+(\d+)K\sused", system_resources
        )
        if r_mem:
            total_mem = int(r_mem.group(1))
            used_mem = int(r_mem.group(2))
            if total_mem > 0:
                mem_util = f"{(used_mem / total_mem) * 100:.2f}%"

        ## STORAGE
        r_used = re.search(r"(\d+)\s+bytes\s+used", dir_output)
        r_total = re.search(r"(\d+)\s+bytes\s+total", dir_output)
        used_storage = int(r_used.group(1)) if r_used else 0
        total_storage = int(r_total.group(1)) if r_total else 0
        if total_storage > 0:
            storage_perc = (used_storage / total_storage) * 100
            storage_util = f"{storage_perc:.2f}%"

        return {
            "cpu_utilization": cpu_util,
            "memory_utilization": mem_util,
            "storage_utilization": storage_util,
        }

    except Exception as e:
        print(f"Errors: {e}")
        return {}


Item = Dict[str, Any]


def show_interface(conn: BaseConnection) -> List[Item]:
    try:
        raw = conn.send_command("show interface", use_textfsm=True)

        # Tell the type checker what TextFSM actually returns:
        show_interfaces = cast(List[Item], raw)

        # Normalize protocol_status
        for item in show_interfaces:
            if not item.get("protocol_status"):
                item["protocol_status"] = item.get("admin_state", "")

        # Unified fields for BOTH IOS and NXOS
        fields = [
            "interface",
            "link_status",
            "protocol_status",
            "description",
            "ip_address",
            "prefix_length",
            "mtu",
            "speed",
            "input_errors",
            "output_errors",
            "crc",
        ]

        filtered: List[Item] = [
            {key: item.get(key, "") for key in fields} for item in show_interfaces
        ]

        return filtered

    except Exception as e:
        print(f"Errors: {e}")
        return []


def show_spanning_tree_detail(conn: BaseConnection, device_type: str):
    print("show_version")


def show_spanning_tree_blockedports(conn: BaseConnection, device_type: str):
    print("show_version")


def show_spanning_tree_root(conn: BaseConnection, device_type: str):
    print("show_version")


def show_mac_address_table(
    conn: BaseConnection,
) -> List[Dict[str, str]]:
    try:
        raw = conn.send_command("show mac address-table", use_textfsm=True)

        # TextFSM output: list of dicts (IOS & NXOS)
        mac_table = cast(List[Item], raw)

        normalized: List[Dict[str, str]] = []

        for item in mac_table:
            if not isinstance(item, dict):
                # Defensive: skip weird entries
                continue

            entry: Dict[str, str] = {}

            # VLAN is common on both
            entry["vlan_id"] = str(item.get("vlan_id", ""))

            # 🔁 Normalize MAC address key
            entry["mac_address"] = (
                str(item.get("mac_address"))
                if item.get("mac_address") is not None
                else str(item.get("destination_address", ""))
            )

            # 🔁 Normalize type
            entry["type"] = str(item.get("type", ""))

            # 🔁 Normalize ports (string in NXOS, list in IOS)
            ports = item.get("ports") or item.get("destination_port") or ""
            if isinstance(ports, list):
                ports = ",".join(str(p) for p in ports)

            entry["ports"] = str(ports)

            normalized.append(entry)

        return normalized

    except Exception as e:
        print(f"Errors: {e}")
        return []


def show_ip_route(conn: BaseConnection, device_type: str):
    try:
        routes = []

        if "nxos" in device_type:
            nxos_routes = conn.send_command("show ip route vrf all", use_textfsm=True)

            if not isinstance(nxos_routes, list):
                return []

            for item in nxos_routes:
                routes.append(
                    {
                        "vrf": item.get("vrf", "default"),
                        "protocol": item.get("protocol", ""),
                        "network": item.get("network", ""),
                        "prefix_length": item.get("prefix_length", ""),
                        "nexthop_ip": item.get("nexthop_ip", ""),
                        "nexthop_if": item.get("nexthop_if", ""),
                    }
                )

            return routes

        default_routes = conn.send_command("show ip route", use_textfsm=True)
        if isinstance(default_routes, list):
            for item in default_routes:
                routes.append(
                    {
                        "vrf": "default",
                        "protocol": item.get("protocol", ""),
                        "network": item.get("network", ""),
                        "prefix_length": item.get("prefix_length", ""),
                        "nexthop_ip": item.get("nexthop_ip", ""),
                        "nexthop_if": item.get("nexthop_if", ""),
                    }
                )

        vrfs = conn.send_command("show vrf", use_textfsm=True)

        if not isinstance(vrfs, list):
            return routes

        for vrf in vrfs:
            vrf_name = vrf.get("name")

            if not vrf_name:
                continue

            if vrf_name.lower() == "default":
                continue

            cmd = f"show ip route vrf {vrf_name}"

            vrf_routes = conn.send_command(cmd, use_textfsm=True)

            if not isinstance(vrf_routes, list):
                continue

            for item in vrf_routes:
                routes.append(
                    {
                        "vrf": vrf_name,
                        "protocol": item.get("protocol", ""),
                        "network": item.get("network", ""),
                        "prefix_length": item.get("prefix_length", ""),
                        "nexthop_ip": item.get("nexthop_ip", ""),
                        "nexthop_if": item.get("nexthop_if", ""),
                    }
                )

        return routes

    except Exception as e:
        print(f"Errors: {e}")
        return None


def show_arp(conn: BaseConnection, device_type: str):
    try:
        arp = []

        if "nxos" in device_type:
            nxos_arp = conn.send_command("show ip arp vrf all", use_textfsm=True)

            if not isinstance(nxos_arp, list):
                return []

            for item in nxos_arp:
                arp.append(
                    {
                        "vrf": item.get("vrf", "default"),
                        "ip_address": item.get("ip_address", ""),
                        "mac_address": item.get("mac_address", ""),
                        "interface": item.get("interface", ""),
                    }
                )

            return arp

        default_arp = conn.send_command("show ip arp", use_textfsm=True)
        if isinstance(default_arp, list):
            for item in default_arp:
                arp.append(
                    {
                        "vrf": item.get("vrf", "default"),
                        "ip_address": item.get("ip_address", ""),
                        "mac_address": item.get("mac_address", ""),
                        "interface": item.get("interface", ""),
                    }
                )

        vrfs = conn.send_command("show vrf", use_textfsm=True)

        if not isinstance(vrfs, list):
            return arp

        for vrf in vrfs:
            vrf_name = vrf.get("name")

            if not vrf_name:
                continue

            if vrf_name.lower() == "default":
                continue

            cmd = f"show ip arp vrf {vrf_name}"

            vrf_routes = conn.send_command(cmd, use_textfsm=True)

            if not isinstance(vrf_routes, list):
                continue

            for item in vrf_routes:
                arp.append(
                    {
                        "vrf": vrf_name,
                        "ip_address": item.get("ip_address", ""),
                        "mac_address": item.get("mac_address", ""),
                        "interface": item.get("interface", ""),
                    }
                )

        return arp

    except Exception as e:
        print(f"Errors: {e}")
        return None


def show_logg(conn: BaseConnection, device_type: str):
    try:
        logs = []
        logg = str(conn.send_command("show logg | in %SYS-5-"))
        logs.extend(re.findall(r"%SYS-5-\S+: .*", logg))
        logs.extend(re.findall(r"SYS-5-\S+: .*", logg))

        return logs

    except Exception as e:
        print(f"Errors: {e}")
        return None


def collect_data_mantools(creds):
    hostname = creds["hostname"]
    device_type = creds["device_type"]

    conn = connect_to_device(creds)

    if conn:
        console.print(
            f"[bold cyan]Connected to {hostname} ({device_type})...[/bold cyan]"
        )

        try:
            show_inv = conn.send_command("show inv")
            show_int_des = conn.send_command("show interface description")
            show_int_status = conn.send_command("show interface status")
            show_int_trunk = conn.send_command("show interface trunk")
            show_int = conn.send_command("show interface")
            show_ip_arp = conn.send_command("show ip arp")
            show_mac_address_table = conn.send_command("show mac address-table")
            show_cdp_nei = conn.send_command("show cdp neighbors")
            show_cdp_nei_det = conn.send_command("show cdp neighbors detail")
            show_lldp_nei = conn.send_command("show lldp neighbors")
            show_lldp_nei_det = conn.send_command("show lldp neighbors detail")

            if "nxos" in device_type:
                show_port_channel = conn.send_command("show port-channel summary")
                show_standby = conn.send_command("show hsrp brief")
            else:
                show_port_channel = conn.send_command("show etherchannel summary")
                show_standby = conn.send_command("show standby brief")

            combined = (
                f"{show_inv}\n"
                f"{show_int_des}\n"
                f"{show_int_status}\n"
                f"{show_int_trunk}\n"
                f"{show_int}\n"
                f"{show_ip_arp}\n"
                f"{show_mac_address_table}\n"
                f"{show_cdp_nei}\n"
                f"{show_cdp_nei_det}\n"
                f"{show_lldp_nei}\n"
                f"{show_lldp_nei_det}\n"
                f"{show_port_channel}\n"
                f"{show_standby}\n"
            )

            return combined
        except Exception as e:
            print(f"Errors: {e}")
            return ""
    else:
        print(f"ERROR: Failed to capture from {hostname}")
        return ""


def collect_devices_data(base_dir=None):
    customer_name = get_customer_name()
    devices = load_devices()
    timestamp = datetime.now().strftime("%d%m%Y")

    if base_dir:
        path = os.path.join(
            base_dir,
            customer_name,
            "legacy",
            "mantools",
            timestamp,
        )
    else:
        path = os.path.join(
            "results",
            customer_name,
            "legacy",
            "mantools",
            timestamp,
        )
    os.makedirs(path, exist_ok=True)

    for dev in devices:
        hostname = dev.get("hostname", "")
        data = collect_data_mantools(dev)
        with open(
            os.path.join(path, f"{customer_name}___{hostname}___{timestamp}.txt"), "w"
        ) as f:
            f.write(data)


def load_devices(file="inventory.csv"):
    devices = []
    try:
        with open(file, "r") as f:
            reader = csv.reader(f, delimiter=";")

            for row in reader:
                if len(row) != 5:
                    continue

                hostname, ip, os_type, username, enc_password = row

                if "apic" in os_type:
                    continue

                device_type = map_os_to_device_type(os_type)
                devices.append(
                    {
                        "hostname": hostname,
                        "ip": ip,
                        "os": os_type,
                        "device_type": device_type,
                        "username": username,
                        "password": enc_password,
                    }
                )

        return devices

    except FileNotFoundError:
        return []


def get_key_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
