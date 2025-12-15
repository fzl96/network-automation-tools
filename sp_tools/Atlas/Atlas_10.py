import time
import pandas as pd
from netmiko import ConnectHandler, redispatch
import re
import sys
import os
import getpass

# memastikan root project (/root) ada di sys.path untuk import sp_tools
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from sp_tools.jumphost import get_jumpserver

from inventory.lib.path import get_data_dir
base_dir = get_data_dir()
file_path = os.path.join(base_dir, "ip_interface_bank.xlsx")


banner = f"""
 ______________________________________________________________________
|:..                                                   ''':::::%%%%%%%%|
|%%%:::::..                      A T L A S                   ''::::%%%%|
|%%%%%%%:::::.....__________________________________________________:::|

Description   : Automated Traceroute with IP to Hostname Mapping
Version       : 1.0
------------------------------------------------------------------------

"""


# fungsi util untuk mapping IP -> hostname dari excel
def find_ips_and_format_output(file_path, ip_list_text):
    # cari semua IPv4 di text traceroute
    ip_addresses = re.findall(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", ip_list_text)
    unique_ips = list(dict.fromkeys(ip_addresses))

    if not unique_ips:
        print("❌ No valid IP addresses found in the provided text.")
        return

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("9. IP Address to Hostname translation")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names

        for target_ip in unique_ips:
            result_found = False

            for sheet_name in sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)

                if "IP-Address" in df.columns:
                    search_result = df[df["IP-Address"].astype(str).str.strip() == target_ip.strip()]

                    if not search_result.empty:
                        host_name = sheet_name.replace(".csv", "")
                        interface = (
                            search_result["Interface"].iloc[0]
                            if "Interface" in search_result.columns
                            else "-"
                        )
                        print(f"{target_ip} -> {host_name} [{interface}]")
                        result_found = True
                        break

            if not result_found:
                print(f"{target_ip} -> not found in the database")

    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"❌ Error: An error occurred - {e}")

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("10. Finish")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


# core logic ATLAS; dipakai baik oleh CLI maupun GUI
def _run_atlas_core(jumpserver, destination, destination_ip):
    print(banner)

    # 1. connect ke jump host
    print(f"\n{'~'*50}\n1. Connecting to the Jump host\n{'~'*50}")
    net_connect = ConnectHandler(**jumpserver)
    print("Jump Server Prompt: {}".format(net_connect.find_prompt()))
    print("\n********** Connected to the Jump host **********")

    # 2. connect ke router tujuan via telnet
    print(f"\n{'~'*50}\n2. Connecting to the Dest Router\n{'~'*50}")
    connection_type = "telnet"
    remote_node = f"{connection_type} {destination}"
    net_connect.write_channel(f"{remote_node}\n")
    time.sleep(3)
    output = net_connect.read_channel()
    print(output)

    # 3. kalau diminta username/password, kirim kredensial langsung dari user input
    if "username" in output.lower():
        router_username = input("Enter router username: ").strip()
        router_password = getpass.getpass("Enter router password: ")

        net_connect.write_channel(f"{router_username}\n")
        time.sleep(2)
        net_connect.write_channel(f"{router_password}\n")

        print(f"\n{'~'*50}\n3. Destination Device Prompt\n{'~'*50}\n")
        print(net_connect.find_prompt())
        print("Router Prompt: {}".format(net_connect.find_prompt()))

        redispatch(net_connect, device_type="cisco_ios")

    # 6. kirim perintah traceroute
    print(f"\n{'~'*50}\n6. Connected to the Router\n{'~'*50}")
    exe_traceroute = f"traceroute mpls ipv4 {destination_ip}/32"
    net_connect.write_channel(f"{exe_traceroute}\n")
    time.sleep(5)
    traceroute_output = net_connect.read_channel()

    print(f"\n{'~'*50}\n7. Traceroute Output\n{'~'*50}")
    print(traceroute_output)
    print("-" * 90)

    # 8. disconnect
    print(f"\n{'~'*50}\n8. Disconnecting from the Router\n{'~'*50}")
    net_connect.disconnect()
    print("Connection successfully disconnected.\n")

    # 9-10. translate IP -> hostname
    find_ips_and_format_output("ip_interface_bank.xlsx", traceroute_output)

    return traceroute_output


# fungsi untuk dipakai GUI – semua input berasal dari GUI
def run_atlas_gui(jump_ip, username, password, port=22, destination=None, destination_ip=None):
    # normalisasi nilai
    jump_ip = (jump_ip or "").strip()
    username = (username or "").strip()
    password = password or ""
    destination = (destination or "").strip()
    destination_ip = (destination_ip or "").strip()
    port = int(port) if port else 22

    if not jump_ip or not username or not password:
        raise ValueError("Jumpserver IP / username / password tidak boleh kosong")
    if not destination:
        raise ValueError("Destination router tidak boleh kosong")
    if not destination_ip:
        raise ValueError("Destination IP untuk traceroute tidak boleh kosong")

    # bentuk dict seperti get_jumpserver()
    jumpserver = {
        "device_type": "terminal_server",
        "ip": jump_ip,
        "username": username,
        "password": password,
        "port": port,
    }

    return _run_atlas_core(jumpserver, destination, destination_ip)


# entrypoint versi CLI – tetap mempertahankan interaksi terminal lama
def interactive_main():
    # minta data jumpserver via helper lama
    jumpserver = get_jumpserver()

    destination = input("Enter the destination to connect (e.g: 'p-d2-bks', 'me-d6-sbr-4'): ").strip()
    destination_ip = input("Enter the destination IPv4 for traceroute: ").strip()

    return _run_atlas_core(jumpserver, destination, destination_ip)


if __name__ == "__main__":
    interactive_main()