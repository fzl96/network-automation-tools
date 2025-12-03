import time
import pandas as pd
from netmiko import ConnectHandler, redispatch
import re
import os
# Import getpass for secure password input
from getpass import getpass 


banner = (f"""
    
 ______________________________________________________________________
|:..                                                   ''':::::%%%%%%%%|
|%%%:::::..                      A T L A S                   ''::::%%%%|
|%%%%%%%:::::.....__________________________________________________:::|
  
Description   : Automated Traceroute with IP to Hostname Mapping
Version       : 1.0
------------------------------------------------------------------------

""")
print(banner)

#This section imports necessary libraries and defines the connection parameters for the jump server.
# Function to read username and password from a .txt file
def read_credentials(file_path):
    with open(file_path, 'r') as cred_file:
        lines = cred_file.readlines()
        username = lines[0].strip()
        password = lines[1].strip()
    return username, password

# Retrieve credentials
username, password = read_credentials('ssh_credentials.txt')

# Define jumpserver configuration
jumpserver = {
    "device_type": "terminal_server",
    "ip": "10.62.170.56",
    "username": username,
    "password": password,
    "port": 22
}
#---------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------
# Here, the script connects to the jump server and confirms the connection by printing the prompt.
# Connect to Jumphost
print(f"\n{'~'*50}\n1. Connecting to the Jump host\n{'~'*50}")
net_connect = ConnectHandler(**jumpserver)
print ("Jump Server Prompt: {}".format(net_connect.find_prompt()))
print(net_connect.find_prompt())
print(f"\n{'*'*10}Connected to the Jump host{'*'*10}")
#---------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------
# This section initiates an SSH connection to the destination router and reads the output.
# Connect to Router
print(f"\n{'~'*50}\n2. Connecting to the Dest Router\n{'~'*50}")
#net_connect.write_channel("telnet p-d2-boo\n")
destination = input("Enter the destination to connect (e.g: 'p-d2-bks', 'me-d6-sbr-4'): ")
connection_type = "telnet"
remote_node = f"{connection_type} {destination}"
net_connect.write_channel(f"{remote_node}\n")
time.sleep(3)
output = net_connect.read_channel()
print(output)
#---------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------
# If prompted for a password, the script sends the password and redispatches the connection to the appropriate device type.
if "username" in output:
    # Read username and password from a .txt file
    with open('tacacs_credentials.txt', 'r') as cred_file:
        lines = cred_file.readlines()
        router_username = lines[0].strip()
        router_password = lines[1].strip()
    
    # Send username and password to the router
    net_connect.write_channel(f"{router_username}\n")
    time.sleep(2)
    net_connect.write_channel(f"{router_password}\n")
    print(f"\n{'~'*50}\n3. Destination Device Prompt\n{'~'*50}\n")
    print(net_connect.find_prompt())
    print("Router Prompt: {}".format(net_connect.find_prompt()))
    redispatch(net_connect, device_type="cisco_ios")

# Print timestamp with day
#print(time.strftime("%a %d-%b-%Y %H:%M:%S WIB", time.localtime()))



# ---
# 6. Mengirim Perintah Traceroute
# ---
print(f"\n{'~'*50}\n6. Connected to the Router\n{'~'*50}")
destination_ip = input("Enter the destination IPv4 for traceroute: ")
exe_traceroute = f"traceroute mpls ipv4 {destination_ip}/32"
net_connect.write_channel(f"{exe_traceroute}\n")
time.sleep(5)
traceroute_output = net_connect.read_channel()
print(f"\n{'~'*50}\n7. Traceroute Output\n{'~'*50}")
print(traceroute_output)
print("------------------------------------------------------------------------------------------")

# ---
# 8. Memutuskan Koneksi
# ---
print(f"\n{'~'*50}\n8. Disconnecting from the Router\n{'~'*50}")
net_connect.disconnect()
print("Connection successfully disconnected.\n")

# ---
# 9. Fungsi untuk Memuat dan Memproses Pemetaan IP
# ---

def find_ips_and_format_output(file_path, ip_list_text):
    """
    Searching for a list of IP addresses and formatting the output as requested.
    """
    ip_addresses = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', ip_list_text)
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
                
                if 'IP-Address' in df.columns:
                    search_result = df[df['IP-Address'].astype(str).str.strip() == target_ip.strip()]

                    
                    if not search_result.empty:
                        host_name = sheet_name.replace(".csv", "")
                        interface = search_result['Interface'].iloc[0]
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

# ---
# 10. Menjalankan fungsi baru setelah traceroute
# ---
find_ips_and_format_output("ip_interface_bank.xlsx", traceroute_output)