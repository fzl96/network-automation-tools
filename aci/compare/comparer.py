import json
import glob
from rich import print as rprint
from aci.snapshot.snapshotter import choose_snapshots
from aci.lib.utils import (
    save_to_excel,
    print_colored_result,
    normalize_faults,
    summarize_interfaces,
    summarize_interface_errors,
    extract_interface_from_dn,
)    
from legacy.customer_context import get_customer_name
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.traceback import install

install(show_locals=True)
console = Console()

DEBUG = True

def debug(msg):
    if DEBUG:
        console.print(f"[dim][DEBUG][/dim] {msg}")


def compare_snapshots(file1, file2):
    with open(file1) as f1, open(file2) as f2:
        before_json = json.load(f1)
        after_json = json.load(f2)

    # APICs that exist in BOTH snapshots
    apics = sorted(set(before_json.keys()) & set(after_json.keys()))
    print("DEBUG snapshot APICs:", apics)
    result = {}


    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task("Comparing APICs", total=len(apics))


        for apic in apics:
            before = before_json.get(apic, {})
            after = after_json.get(apic, {})

            if not before or not after:
                debug(f"{apic}: skipped (missing snapshot data)")
                progress.advance(task)
                continue

            result[apic] = {}

            # =====================
            # Fabric health
            # =====================
            result[apic]["fabric_health"] = {
                "before": before.get("fabric_health"),
                "after": after.get("fabric_health"),
            }
            debug(f"{apic}: fabric health captured")

            # =====================
            # Faults
            # =====================
            before_faults = normalize_faults(before.get("faults", []))
            after_faults = normalize_faults(after.get("faults", []))

            new_dns = sorted(after_faults.keys() - before_faults.keys())
            cleared_dns = sorted(before_faults.keys() - after_faults.keys())

            result[apic]["new_faults"] = [after_faults[dn] for dn in new_dns]
            result[apic]["cleared_faults"] = [before_faults[dn] for dn in cleared_dns]

            debug(
                f"{apic}: faults new={len(result[apic]['new_faults'])}, "
                f"cleared={len(result[apic]['cleared_faults'])}"
            )
            # =====================
            # Endpoints
            # =====================
            before_eps = {
                ep["mac"]: {
                    "node": ep["node"],
                    "interface": ep["interface"],
                    "mac": ep["mac"],
                    "vlan": ep["vlan"],
                    "epg_descr": ep["epg_descr"],
                    "dn": ep["dn"],
                    "ip": (ep.get("ip") or ""),
                }
                for ep in before.get("endpoints", [])
            }
            after_eps = {
                ep["mac"]: {
                    "node": ep["node"],
                    "interface": ep["interface"],
                    "mac": ep["mac"],
                    "vlan": ep["vlan"],
                    "epg_descr": ep["epg_descr"],
                    "dn": ep["dn"],
                    "ip": (ep.get("ip") or ""),
                }
                for ep in after.get("endpoints", [])
            }

            before_dns = set(before_eps.keys())
            after_dns = set(after_eps.keys())
            new_endpoints = []
            missing_endpoints = []
            new_endpoints_mac = sorted(after_dns - before_dns)
            missing_endpoints_mac = sorted(before_dns - after_dns)
            for mac in new_endpoints_mac:
                temp = after_eps.get(mac, {})
                new_endpoints.append(temp)

            for mac in missing_endpoints_mac:
                temp = before_eps.get(mac)
                missing_endpoints.append(temp)

            result[apic]["new_endpoints"] = new_endpoints
            result[apic]["missing_endpoints"] = missing_endpoints

            debug(
                f"{apic}: endpoints new={len(result[apic]['new_endpoints'])}, "
                f"missing={len(result[apic]['missing_endpoints'])}"
            )

            # =====================    
            # Interface status
            # =====================
            before_intfs = summarize_interfaces(
                before.get("interfaces", []),
                before.get("interface_errors", []),
            )

            after_intfs = summarize_interfaces(
                after.get("interfaces", []),
                after.get("interface_errors", []),
            )

            status_changed = []

            for k in before_intfs.keys() & after_intfs.keys():
                before_entry = before_intfs[k]
                after_entry = after_intfs[k]

                if before_entry["status"] != after_entry["status"]:
                    status_changed.append(
                        f"{k}|{before_entry['node']}|"
                        f"{before_entry['status']} ➜ {after_entry['status']}"
                    )

            intf_changes = {
                "status_changed": status_changed,
                "missing": sorted(set(before_intfs) - set(after_intfs)),
                "new": sorted(set(after_intfs) - set(before_intfs)),
            }

            result[apic]["interface_changes"] = intf_changes

            debug(
                f"{apic}: interfaces changed="
                f"{len(intf_changes['status_changed'])}, "
                f"missing={len(intf_changes['missing'])}, "
                f"new={len(intf_changes['new'])}"
            )
                    

            # =====================
            # Interface Errors
            # =====================
            interfaces_map = {}
            po_map = {}
            interfaces = after.get("interfaces", [])
            pos = after.get("pc_aggr", [])

            for item in interfaces:
                attr = item.get("l1PhysIf", {}).get("attributes", {})

                dn = attr.get("dn", "")

                node = None
                for part in dn.split("/"):
                    if part.startswith("node-"):
                        node = part
                        break

                entry = {
                    "node": node,
                    "id": attr.get("id", ""),
                    "descr": attr.get("descr", ""),
                }
                interfaces_map[f"{node}-{attr.get('id', 'none')}"] = entry

                for po in pos:
                    attr = po.get("pcAggrIf", {}).get("attributes", {})
                    dn = attr.get("dn", "")
                    node = None
                    for part in dn.split("/"):
                        if part.startswith("node-"):
                            node = part
                            break

                    po_entry = {
                        "node": node,
                        "id": attr.get("id", ""),
                        "name": attr.get("name", ""),
                    }

                    po_map[f"{node}-{attr.get('id', 'None')}"] = po_entry

            before_errs = summarize_interface_errors(before.get("interface_errors", []))
            after_errs = summarize_interface_errors(after.get("interface_errors", []))
            error_changes = {}
            for dn in set(before_errs) | set(after_errs):
                b = before_errs.get(dn, 0)
                a = after_errs.get(dn, 0)
                if a > b:
                    error_changes[dn] = f"{b} ➜ {a}"
                result[apic]["interface_error_changes"] = error_changes
            debug(f"{apic}: interface error increases={len(error_changes)}")

            # =====================
            # CRC Errors
            # =====================
            before_crc = {}
            for e in before.get("crc_errors", []):
                if "rmonEtherStats" in e and "attributes" in e["rmonEtherStats"]:
                    dn = e["rmonEtherStats"]["attributes"].get("dn")
                    # Note: The key is "cRCAlignErrors" not "crcAlignErrors"
                    crc_align_errors = int(
                        e["rmonEtherStats"]["attributes"].get("cRCAlignErrors", 0)
                    )
                    if dn:
                        before_crc[dn] = crc_align_errors

            after_crc = {}
            for e in after.get("crc_errors", []):
                if "rmonEtherStats" in e and "attributes" in e["rmonEtherStats"]:
                    dn = e["rmonEtherStats"]["attributes"].get("dn")
                    # Note: The key is "cRCAlignErrors" not "crcAlignErrors"
                    crc_align_errors = int(
                        e["rmonEtherStats"]["attributes"].get("cRCAlignErrors", 0)
                    )
                    if dn:
                        after_crc[dn] = crc_align_errors

            all_interfaces = set(before_crc.keys()) | set(after_crc.keys())
            crc_changes = []
            for dn in all_interfaces:
                b = before_crc.get(dn, 0)
                a = after_crc.get(dn, 0)

                if a > b:
                    # Extract interface name for better readability
                    node, port = extract_interface_from_dn(dn)
                    if node is None:
                        continue

                    err_eps = [
                        ep
                        for ep in after_eps.values()
                        if ep["node"] == node.split("-")[1] and ep["interface"] == port
                    ]

                    crc_changes.append(
                        {
                            "before": b,
                            "after": a,
                            "node": node,
                            "interface": port
                            if not port.startswith("po")  # type: ignore
                            else po_map.get(f"{node}-{port}", {}).get("name", port),
                            "interface_descr": interfaces_map.get(f"{node}-{port}", {}).get(
                                "descr", ""
                            ),
                            "endpoints": err_eps,
                        }
                    )

            result[apic]["crc_error_changes"] = crc_changes

            debug(f"{apic}: interface crc changes={len(crc_changes)}")

            # =====================
            # Interface Errors
            # =====================
            before_drop = {}
            for e in before.get("drop_errors", []):
                if "rmonEgrCounters" in e and "attributes" in e["rmonEgrCounters"]:
                    dn = e["rmonEgrCounters"]["attributes"].get("dn")
                    drop_errors = int(
                        e["rmonEgrCounters"]["attributes"].get("bufferdroppkts", 0)
                    )
                    if dn:
                        before_drop[dn] = drop_errors
            after_drop = {}
            for e in after.get("drop_errors", []):
                if "rmonEgrCounters" in e and "attributes" in e["rmonEgrCounters"]:
                    dn = e["rmonEgrCounters"]["attributes"].get("dn")
                    drop_errors = int(
                        e["rmonEgrCounters"]["attributes"].get("bufferdroppkts", 0)
                    )
                    if dn:
                        after_drop[dn] = drop_errors

            all_interfaces = set(before_drop.keys()) | set(after_drop.keys())
            drop_changes = []
            for dn in all_interfaces:
                b = before_drop.get(dn, 0)
                a = after_drop.get(dn, 0)
                if a > b:
                    node, intf = extract_interface_from_dn(dn)
                    if node is None:
                        continue
                    err_eps = [
                        ep
                        for ep in after_eps.values()
                        if ep["node"] == node.split("-")[1] and ep["interface"] == intf
                    ]

                    drop_changes.append(
                        {
                            "before": b,
                            "after": a,
                            "node": node,
                            "interface": intf
                            if not intf.startswith("po")  # type: ignore
                            else po_map.get(f"{node}-{intf}", {}).get("name", intf),
                            "interface_descr": interfaces_map.get(f"{node}-{intf}", {}).get(
                                "descr", ""
                            ),
                            "endpoints": err_eps,
                        }
                    )

            result[apic]["drop_error_changes"] = drop_changes
            debug(f"{apic}: interface drop changes={len(drop_changes)}")

            # =====================
            # Output Errors
            # =====================
            before_output = {}
            for e in before.get("output_errors", []):
                if "rmonIfOut" in e and "attributes" in e["rmonIfOut"]:
                    dn = e["rmonIfOut"]["attributes"].get("dn")
                    output_errors = int(e["rmonIfOut"]["attributes"].get("errors", 0))
                    if dn:
                        before_output[dn] = output_errors
            after_output = {}
            for e in after.get("output_errors", []):
                if "rmonIfOut" in e and "attributes" in e["rmonIfOut"]:
                    dn = e["rmonIfOut"]["attributes"].get("dn")
                    output_errors = int(e["rmonIfOut"]["attributes"].get("errors", 0))
                    if dn:
                        after_output[dn] = output_errors

            output_changes = []
            all_interfaces = set(before_output.keys()) | set(after_output.keys())
            for dn in all_interfaces:
                b = before_output.get(dn, 0)
                a = after_output.get(dn, 0)
                if a > b:
                    node, intf = extract_interface_from_dn(dn)

                    # === PATCH: Safe interface handling ===
                    if intf is None:
                        safe_interface = ""
                    else:
                        safe_interface = (
                            po_map.get(f"{node}-{intf}", {}).get("name", intf)
                            if intf.startswith("po")
                            else intf
                        )
                    # =======================================

                    err_eps = [
                        ep
                        for ep in after_eps.values()
                        if ep["node"] == node and ep["interface"] == intf
                    ]

                    output_changes.append(
                        {
                            "before": b,
                            "after": a,
                            "node": node,
                            "interface": safe_interface,
                            "interface_descr": interfaces_map.get(f"{node}-{intf}", {}).get(
                                "descr", ""
                            ),
                            "endpoints": err_eps,
                        }
                    )

            result[apic]["output_error_changes"] = output_changes
            debug(f"{apic}: interface output error changes={len(output_changes)}")

            # =====================
            # URIB Route
            # =====================
            before_routes = {
                r["uribv4Route"]["attributes"]["dn"] for r in before.get("urib_routes", [])
            }
            after_routes = {
                r["uribv4Route"]["attributes"]["dn"] for r in after.get("urib_routes", [])
            }
            route_changes = {
                "missing": sorted(before_routes - after_routes),
                "new": sorted(after_routes - before_routes),
            }
            result[apic]["urib_route_changes"] = route_changes
            debug(f"{apic}: urib route changes={len(route_changes)}")

        return result
        



def compare_select(base_dir):
    print("\n📂 Selecting snapshots to compare...")
    file1, file2 = choose_snapshots(base_dir)
    if file1 and file2:
        print(f"📊 Comparing '{file1}' and '{file2}'...")
        result = compare_snapshots(file1, file2)     
        print_colored_result(result)
        save_to_excel(result, base_dir=base_dir)
    else:
        print("❌ No valid snapshots selected.")        

def compare_last_two(base_dir):
    customer_name = get_customer_name()
    if base_dir:
        print("base dir")
        files = sorted(
            glob.glob(f"{base_dir}/{customer_name}/aci/snapshot/*_snapshot_*.json")
        )
    else:
        files = sorted(
            glob.glob(f"results/{customer_name}/aci/snapshot/*_snapshot_*.json")
        )
    if len(files) < 2:
        print("❌ Not enough snapshot files found to compare.")
    else:
        before, after = files[-2], files[-1]
        print(f"📊 Comparing:\n  BEFORE: {before}\n  AFTER:  {after}")
        result = compare_snapshots(before, after)
        print_colored_result(result)
        save_to_excel(result, base_dir=base_dir)
