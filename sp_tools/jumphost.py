import getpass

def get_jumpserver():
    ip = input("Enter Jumpserver IP: ").strip()
    username = input("Enter Username: ").strip()
    password = getpass.getpass("Enter Password: ")
    port_input = input("Enter Port (default 22): ").strip()

    port = int(port_input) if port_input else 22

    return {
        "device_type": "terminal_server",
        "ip": ip,
        "username": username,
        "password": password,
        "port": port
    }
