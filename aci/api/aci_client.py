import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning  # type: ignore
from rich.console import Console
console = Console()
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # type: ignore


def login(apic_ip, username, password):
    url = f"https://{apic_ip}/api/aaaLogin.json"
    payload = {"aaaUser": {"attributes": {"name": username, "pwd": password}}}
    response = requests.post(url, json=payload, verify=False)
    response.raise_for_status()
    return response.cookies, apic_ip


def get_fabric_health(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/fabricHealthTotal.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Fabric health data retrieved from {apic_ip}.[/green]")
    return int(r.json()["imdata"][0]["fabricHealthTotal"]["attributes"]["cur"])


def get_faults(cookies, apic_ip):
    url = f'https://{apic_ip}/api/node/class/faultInst.json?query-target-filter=eq(faultInst.severity,"critical")'
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Fault data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_interface_status(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/l1PhysIf.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Interface status data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_endpoints(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/fvCEp.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Endpoint data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_epgs(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/fvAEPg.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ EPG data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_endpoints_with_ip(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/fvCEp.json?rsp-subtree=children&rsp-subtree-class=fvIp"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Endpoints with IP data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_urib_routes(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/uribv4Route.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ URIB routes data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_interface_errors(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/ethpmPhysIf.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Interface errors data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_crc_errors(cookies, apic_ip):
    """Get CRC error statistics from rmonEtherStats"""
    url = f"https://{apic_ip}/api/node/class/rmonEtherStats.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ CRC errors data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_drop_errors(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/rmonEgrCounters.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Drop errors data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_output_errors(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/rmonIfOut.json"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Output errors data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_output_path_ep(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/fabricPathEp.json?rsp-subtree=children&rsp-subtree-class=fabricRsPathToIf"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Path endpoint data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])


def get_pc_aggr(cookies, apic_ip):
    url = f"https://{apic_ip}/api/node/class/pcAggrIf.json?rsp-subtree=children&rsp-subtree-class=pcRsMbrIfs"
    r = requests.get(url, cookies=cookies, verify=False)
    console.print(f"[green]✓ Port-channel aggregation data retrieved from {apic_ip}.[/green]")
    return r.json().get("imdata", [])
