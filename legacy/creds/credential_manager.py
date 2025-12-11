import os
import json
from cryptography.fernet import Fernet
from legacy.lib.utils import get_key_path

BASE_DIR = os.path.dirname(__file__)
KEY_FILE = os.path.join(BASE_DIR, "key.key")
CRED_FILE = os.path.join(BASE_DIR, "credentials.json")


def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)


def load_key():
    key_path = get_key_path(os.path.join("legacy", "creds", "key.key"))
    with open(key_path, "rb") as key_file:
        return key_file.read()


def save_credentials(profile_name, username, password):
    generate_key()
    key = load_key()
    fernet = Fernet(key)

    if os.path.exists(CRED_FILE):
        with open(CRED_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[profile_name] = {
        "username": fernet.encrypt(username.encode()).decode(),
        "password": fernet.encrypt(password.encode()).decode(),
    }

    with open(CRED_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"✅ Credentials saved for profile '{profile_name}'.")


def load_credentials(profile_name="default"):
    if not os.path.exists(CRED_FILE):
        print("⚠️ No saved credentials found.")
        return None, None

    key = load_key()
    fernet = Fernet(key)

    with open(CRED_FILE, "r") as f:
        data = json.load(f)

    if profile_name not in data:
        print(f"⚠️ No credentials found for profile '{profile_name}'.")
        return None, None

    enc_user = data[profile_name]["username"]
    enc_pass = data[profile_name]["password"]

    username = fernet.decrypt(enc_user.encode()).decode()
    password = fernet.decrypt(enc_pass.encode()).decode()

    return username, password


def list_profiles():
    if not os.path.exists(CRED_FILE):
        return []

    with open(CRED_FILE, "r") as f:
        data = json.load(f)

    return list(data.keys())
