#!/usr/bin/env python3
import shutil
import sys
import os
import time
import pyfiglet
from rich.console import Console
from rich.panel import Panel
from aci.api.aci_client import login
from aci.snapshot.snapshotter import take_all_snapshots
from aci.compare.comparer import (
    compare_select,
    compare_last_two,
)
from aci.healthcheck.checklist_aci import main_healthcheck_aci
from legacy.customer_context import get_customer_name

console = Console()
customer_name = get_customer_name()
# ============================================================
# Utility Functions
# ============================================================

def clear_screen():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def pause(message="\nPress ENTER to continue..."):
    green = "\033[32m"  # Green
    reset = "\033[0m"
    input(f"{green}{message}{reset}")


def slow_print(text, delay=0.02):
    """Print text with smooth typing effect."""
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

    ascii_title = pyfiglet.figlet_format("ACI TOOLS", font="standard")

    for line in ascii_title.splitlines():
        print(f"{red}{line.center(width)}{reset}")

    print()  # spacing

# ============================================================
# Main Menu
# ============================================================


def show_menu():
    console.print("\n")
    menu_text = """
    [bold]1.[/bold] Take snapshot of all ACI systems

    [bold]2.[/bold] Run ACI Health check

    [bold]3.[/bold] Compare last two snapshots

    [bold]4.[/bold] Compare any two snapshots

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
            slow_print(f"{green}{"\n⏳ Taking snapshots..."}{reset}")
            take_all_snapshots(base_dir)
            pause()

        elif choice == "2":
            slow_print(f"{green}{"\n⏳ Running ACI health check..."}{reset}")
            main_healthcheck_aci(base_dir=base_dir)
            pause()

        elif choice == "3":
            slow_print(f"{green}{"\n🔍 Comparing last two snapshots..."}{reset}")
            compare_last_two(base_dir)
            pause()

        elif choice == "4":
            slow_print(f"{green}{"\n📂 Selecting snapshots to compare..."}{reset}")
            compare_select(base_dir)
            pause()

        elif choice == "q":
            slow_print(f"{green}{"\nExit ACI Tools..."}{reset}")
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
