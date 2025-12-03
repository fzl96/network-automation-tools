#!/usr/bin/env python3
"""
legacy_main.py
Professional, clean interface for Legacy Network Tools
"""

import sys
import os
import time
import getpass
from legacy.creds.credential_manager import save_credentials, load_credentials
from legacy.inventory.inventory import create_inventory, show_inventory
from legacy.backup_config.backup import run_backup
from legacy.lib.utils import collect_devices_data
from legacy.lib.snapshot import take_snapshot
from legacy.lib.compare import compare


# ============================================================
# Utility Functions
# ============================================================


def clear_screen():
    """Clear terminal screen for clean display"""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\nPress ENTER to continue..."):
    """Pause execution for user input"""
    input(message)


def slow_print(text, delay=0.02):
    """Smooth typewriter-style output"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_header():
    """Display header"""
    clear_screen()
    print("=" * 60)
    print("🧩  LEGACY NETWORK TOOLS".center(60))
    print("=" * 60)
    print()


def show_menu():
    """Display main menu options"""
    print("Available Actions")
    print("-" * 60)
    print("1. Save credentials securely")
    print("2. Create or update device inventory")
    print("3. Backup device configurations")
    print("4. Show inventory list")
    print("5. Take Snapshot + Health Check")
    print("6. Compare Snapshot")
    print("7. Mantools Online")
    print("q. Exit")
    print("-" * 60)


# ============================================================
# Main Logic
# ============================================================


def main():
    base_dir = None
    while True:
        print_header()
        show_menu()

        choice = input("\nSelect an option (1-4 or q): ").strip().lower()

        if choice == "1":
            slow_print("\n🔐 Saving credentials securely...")
            username = input("Enter username: ").strip()
            password = getpass.getpass("Enter Password (default hidden): ")
            save_credentials("default", username, password)
            slow_print("✅ Credentials saved successfully!")
            pause()

        elif choice == "2":
            username, password = load_credentials()
            if not username or not password:
                print(
                    "\n⚠️  No saved credentials found. Please save credentials first (option 1)."
                )
                pause()
                continue
            slow_print("\n📋 Creating or updating inventory...")
            create_inventory(username, password)
            pause()

        elif choice == "3":
            username, password = load_credentials()
            if not username or not password:
                print(
                    "\n⚠️  No saved credentials found. Please save credentials first (option 1)."
                )
                pause()
                continue
            slow_print("\n💾 Running configuration backup...")
            run_backup(username, password)
            pause()

        elif choice == "4":
            slow_print("\n📄 Displaying inventory list...")
            show_inventory()
            pause()

        elif choice == "5":
            slow_print("\n📄 Taking snapshots and health check...")
            take_snapshot(base_dir)
            pause()

        elif choice == "6":
            slow_print("\n📄 Comparing snapshots...")
            compare(base_dir)
            pause()

        elif choice == "7":
            slow_print("\n📄 Running tool...")
            collect_devices_data(base_dir)
            pause()

        elif choice == "q":
            slow_print("\nExiting Legacy Network Tools...")
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
