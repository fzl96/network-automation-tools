import os
import json
from cryptography.fernet import Fernet
from pathlib import Path
import tempfile
from inventory.lib.session_dir import get_session_dir
from inventory.lib.crypto_paths import KEY_FILE,CRED_FILE

# ---------------------------
# Key management
# ---------------------------
def generate_key():
    if not KEY_FILE.exists():
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)

def load_key():
    generate_key()
    return KEY_FILE.read_bytes()

# ---------------------------
# Credentials management
# ---------------------------
def save_credentials(profile_name, username, password):
    key = load_key()
    fernet = Fernet(key)

    if CRED_FILE.exists():
        data = json.loads(CRED_FILE.read_text())
    else:
        data = {}

    data[profile_name] = {
        "username": fernet.encrypt(username.encode()).decode(),
        "password": fernet.encrypt(password.encode()).decode(),
    }

    CRED_FILE.write_text(json.dumps(data, indent=4))
    print(f"✅ Credentials saved for profile '{profile_name}'.")

def load_credentials(profile_name="default"):
    if not CRED_FILE.exists():
        print("⚠️ No saved credentials found.")
        return None, None

    key = load_key()
    fernet = Fernet(key)

    data = json.loads(CRED_FILE.read_text())
    if profile_name not in data:
        print(f"⚠️ No credentials found for profile '{profile_name}'.")
        return None, None

    enc_user = data[profile_name]["username"]
    enc_pass = data[profile_name]["password"]

    username = fernet.decrypt(enc_user.encode()).decode()
    password = fernet.decrypt(enc_pass.encode()).decode()
    return username, password

def list_profiles():
    if not CRED_FILE.exists():
        return []
    data = json.loads(CRED_FILE.read_text())
    return list(data.keys())
