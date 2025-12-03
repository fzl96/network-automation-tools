#!/usr/bin/env python3
"""
aci_main.py
Professional and consistent CLI for Cisco ACI Snapshot Tools
"""

import json
import getpass
import glob
import requests
from datetime import datetime
from typing import Tuple, Optional
from requests.cookies import RequestsCookieJar
from aci.api.aci_client import login
from aci.snapshot.snapshotter import take_snapshot, list_snapshots, choose_snapshots
from aci.compare.comparer import (
    compare_snapshots,
    print_colored_result,
    save_to_xlsx,
    save_to_excel,
)
from aci.healthcheck.checklist_aci import main_healthcheck_aci
import sys
import os
import time
from legacy.customer_context import get_customer_name
customer_name = get_customer_name()
# ============================================================
# Utility Functions
# ============================================================


def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\nPress ENTER to continue..."):
    """Pause execution for user input."""
    input(message)


def slow_print(text, delay=0.02):
    """Print text with smooth typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_header():
    """Display main header."""
    clear_screen()
    print("=" * 60)
    print("🌐  CISCO ACI SNAPSHOT MANAGER".center(60))
    print("=" * 60)
    print()


# ============================================================
# ACI Utility Functions
# ============================================================


def get_credentials() -> Tuple[str, str, str]:
    """Get APIC credentials from user input, without defaults."""

    # APIC IP
    while True:
        apic_ip = input("Enter APIC IP: ").strip()
        if apic_ip:
            break
        print("APIC IP cannot be empty.")

    # Username
    while True:
        username = input("Enter Username: ").strip()
        if username:
            break
        print("Username cannot be empty.")

    # Password
    while True:
        password = getpass.getpass("Enter Password: ").strip()
        if password:
            break
        print("Password cannot be empty.")

    return apic_ip, username, password


def apic_login(
    apic_ip: str, username: str, password: str
) -> Optional[RequestsCookieJar]:
    """Authenticate to APIC and return session cookies."""
    login_url = f"https://{apic_ip}/api/aaaLogin.json"
    auth_payload = {"aaaUser": {"attributes": {"name": username, "pwd": password}}}

    try:
        resp = requests.post(login_url, json=auth_payload, verify=False, timeout=30)
        if resp.status_code != 200:
            print(f"✗ Login failed with status code: {resp.status_code}")
            return None

        data = resp.json()
        if "imdata" in data and len(data["imdata"]) > 0:
            if isinstance(data["imdata"][0], dict) and "error" in data["imdata"][0]:
                print("✗ Authentication failed: Invalid credentials.")
                return None

        print(f"✓ Successfully authenticated to APIC {apic_ip}")
        return resp.cookies

    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to APIC at {apic_ip}")
    except requests.exceptions.Timeout:
        print("✗ Connection timeout.")
    except Exception as e:
        print(f"✗ Login failed: {str(e)}")

    return None


def timestamp_filename(base: str) -> str:
    """Generate timestamped filename for snapshots."""
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M")
    return f"{base}_{ts}.json"


# ============================================================
# Main Menu
# ============================================================


def show_menu():
    print("Available Actions")
    print("-" * 60)
    print("1. Take snapshot")
    print("2. Run ACI health check")
    print("3. Compare last two snapshots")
    print("4. Compare any two snapshots")
    print("q. Exit")
    print("-" * 60)


def main():
    base_dir = None
 #   customer_name = "MSI"

    while True:
        print_header()
        show_menu()

        choice = input("\nSelect an option (1–4 or q): ").strip().lower()

        if choice == "1":
            slow_print("\n📸 Taking snapshot...")
            apic_ip, username, password = get_credentials()
            cookies = apic_login(apic_ip, username, password)
            if cookies:
                cookies, apic_base = login(apic_ip, username, password)
                # Optional base_dir argument
                take_snapshot(
                    cookies, apic_base, f"{customer_name}_snapshot", base_dir=base_dir
                )
                slow_print("✅ Snapshot completed successfully!")
            else:
                print("❌ Could not authenticate to APIC.")
            pause()

        elif choice == "2":
            slow_print("\n🩺 Running ACI health check...")
            # Optional base_dir argument
            main_healthcheck_aci(base_dir=base_dir)
            pause()

        elif choice == "3":
            slow_print("\n🔍 Comparing last two snapshots...")
            if base_dir:
                files = sorted(glob.glob(f"{base_dir}/snapshot/*.snapshot_*.json"))
            else:
                files = sorted(glob.glob("aci/results/snapshot/*.snapshot_*.json"))
            if len(files) < 2:
                print("❌ Not enough snapshot files found to compare.")
            else:
                before, after = files[-2], files[-1]
                print(f"📊 Comparing:\n  BEFORE: {before}\n  AFTER:  {after}")
                result = compare_snapshots(before, after)
                print_colored_result(result)
                save_to_excel(base_dir=base_dir)
                print("✅ Comparison results saved to Excel.")
            pause()

        elif choice == "4":
            slow_print("\n📂 Selecting snapshots to compare...")
            file1, file2 = choose_snapshots(base_dir=base_dir)
            if file1 and file2:
                print(f"📊 Comparing '{file1}' and '{file2}'...")
                result = compare_snapshots(file1, file2)
                print_colored_result(result)
                save_to_excel(result, base_dir=base_dir)
                print("✅ Comparison results saved to Excel.")
            else:
                print("❌ No valid snapshots selected.")
            pause()

        elif choice == "q":
            slow_print("\nExiting Cisco ACI Snapshot Manager...")
            time.sleep(0.3)
            print("✅ Goodbye! 👋")
            break

        else:
            print("\n❌ Invalid selection. Please try again.")
            pause()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting gracefully...")
        sys.exit(0)
