#!/usr/bin/env python3
import sys
import os
import time
import getpass
import pyfiglet
import shutil
from rich.console import Console
from rich.panel import Panel
from legacy.creds.credential_manager import save_credentials, load_credentials
from legacy.backup_config.backup import run_backup
from legacy.lib.utils import collect_devices_data
from legacy.lib.snapshot import take_snapshot
from legacy.lib.compare import compare

console = Console()
# ============================================================
# Utility Functions
# ============================================================


def clear_screen():
    """Clear terminal screen for clean display"""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\nPress ENTER to continue..."):
    green = "\033[32m"  # Green
    reset = "\033[0m"
    input(f"{green}{message}{reset}")


def slow_print(text, delay=0.02):
    """Smooth typewriter-style output"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def get_terminal_width(default=100):
    """Return current terminal width or a default if detection fails"""
    try:
        width = shutil.get_terminal_size().columns
        return width
    except:
        return default

def print_header():
    """Display header with colored logo and big title"""
    clear_screen()
    width = get_terminal_width()
    red = "\033[31m"
    reset = "\033[0m"

    print()  # spacing

    ascii_title = pyfiglet.figlet_format("LEGACY TOOLS", font="standard")

    for line in ascii_title.splitlines():
        print(f"{red}{line.center(width)}{reset}")

    print()  # spacing

def show_menu():
    console.print("\n")
    menu_text = """
    [bold]1.[/bold] Save credentials securely

    [bold]2.[/bold] Backup Device Configurations

    [bold]3.[/bold] Take Snapshot and Health Check

    [bold]4.[/bold] Compare Snapshot

    [bold]5.[/bold] Mantools Online
    
    [bold]q.[/bold] Exit
    """
    console.print(
        Panel(
            menu_text,
            title="[bold]🧰 Available Tools[/bold]",
            title_align="left",
            border_style="grey37",
            padding=(1, 2),
        )
    )


# ============================================================
# Main Logic
# ============================================================


def main():
    base_dir = None
    while True:
        print_header()
        show_menu()
        green = "\033[32m"
        reset = "\033[0m"

        choice = input("\nSelect an option (1-4 or q): ").strip().lower()

        if choice == "1":
            slow_print(f"{green}{"\n🔐 Saving credentials securely..."}{reset}")
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
            slow_print(f"{green}{"\n💾 Running configuration backup..."}{reset}")
            run_backup(username, password)

        elif choice == "3":
            slow_print(f"{green}{"\n⏳ Taking snapshots and health check..."}{reset}")            
            take_snapshot(base_dir)
            pause()

        elif choice == "4":
            slow_print(f"{green}{"\n🔍  Comparing snapshots..."}{reset}")   
            compare(base_dir)
            pause()

        elif choice == "5":
            slow_print(f"{green}{"\n⏳ Collecting log for mantools online..."}{reset}")               
            collect_devices_data(base_dir)
            pause()

        elif choice == "q":
            slow_print(f"{green}{"\nExit Legacy Tools..."}{reset}")               
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
