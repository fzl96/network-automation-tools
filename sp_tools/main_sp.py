#!/usr/bin/env python3
"""
legacy_main.py
Professional, clean interface for Legacy Network Tools
"""

import subprocess
import sys
import os
import time

# ============================================================
# Script Runner
# ============================================================

def run_script(filename):
    """Run external python script cleanly"""
    script_path = os.path.join(os.path.dirname(__file__), filename)

    if not os.path.exists(script_path):
        slow_print(f"❌ ERROR: Script '{filename}' not found!")
        pause()
        return

    slow_print(f"\n▶ Running {filename}...\n")
    time.sleep(0.3)

    # Run script smoothly
    subprocess.call([sys.executable, script_path])

    print("\n✅ Script finished.")
    pause()

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
    print("1. Atlas_v1")
    print("2. CRCell_v1")
    print("3. Snipe_v1")
    print("4. Xray_v1")
    print("q. Exit")
    print("-" * 60)


# ============================================================
# Main Logic
# ============================================================


def main():
    while True:
        print_header()
        show_menu()

        choice = input("\nSelect an option (1-4 or q): ").strip().lower()

        if choice == "1":
            run_script("Atlas_v1/Atlas_10.py")

        elif choice == "2":
            run_script("CRCell_v1/CRC_Cell_15.py")

        elif choice == "3":
            run_script("Snipe_v1/snipe_R.py")

        elif choice == "4":
            run_script("Xray_v1/xray_8.py")

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
