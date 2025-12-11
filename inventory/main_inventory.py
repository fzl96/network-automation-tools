#!/usr/bin/env python3
import sys
import os
import time
from pathlib import Path
import os
import pyfiglet
import shutil
from rich.console import Console
from rich.panel import Panel

from legacy.creds.credential_manager import load_credentials

from inventory.lib.create_inventory import create_inventory
from inventory.lib.show_inventory import show_inventory


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

    ascii_title = pyfiglet.figlet_format("INVENTORY", font="standard")

    for line in ascii_title.splitlines():
        print(f"{red}{line.center(width)}{reset}")

    print()  # spacing

# ============================================================
# Main Menu
# ============================================================


def show_menu():
    console.print("\n")
    menu_text = """
    [bold]1.[/bold] Create and Update Device Inventory

    [bold]2.[/bold] Show Inventory list

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

def main():
    base_dir = None

    while True:
        print_header()
        show_menu()
        green = "\033[32m"
        reset = "\033[0m"

        choice = input("\nSelect an option (1–4 or q): ").strip().lower()

        if choice == "1":
            username, password = load_credentials()
            if not username or not password:
                print(
                    "\n⚠️  No saved credentials found. Please save credentials first (option 1)."
                )
                pause()
                continue
            slow_print(f"{green}{"\n📋 Creating or updating inventory..."}{reset}")
            create_inventory(username, password)
            pause()

        elif choice == "2":
            slow_print(f"{green}\n📄 Displaying inventory list...{reset}")
            show_inventory()
            pause()


        elif choice == "q":
            slow_print(f"{green}{"\nExit Inventory..."}{reset}")
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
