#!/usr/bin/env python3
"""
aci_main.py
Professional and consistent CLI for Cisco ACI Snapshot Tools
"""

import getpass
import requests
from datetime import datetime
from typing import Tuple, Optional
from requests.cookies import RequestsCookieJar
from aci.api.aci_client import login
from aci.snapshot.snapshotter import take_all_snapshots
from aci.compare.comparer import (
    compare_select,
    compare_last_two,
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

    while True:
        print_header()
        show_menu()

        choice = input("\nSelect an option (1–4 or q): ").strip().lower()

        if choice == "1":
            take_all_snapshots(base_dir)
            pause()

        elif choice == "2":
            slow_print("\n🩺 Running ACI health check...")
            main_healthcheck_aci(base_dir=base_dir)
            pause()

        elif choice == "3":
            slow_print("\n🔍 Comparing last two snapshots...")
            compare_last_two(base_dir)
            pause()

        elif choice == "4":
            slow_print("\n📂 Selecting snapshots to compare...")
            compare_select(base_dir)
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
