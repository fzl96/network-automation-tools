#!/usr/bin/env python3
import sys
import os
import time
import getpass
import pyfiglet
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from inventory.lib.credential_manager import load_credentials
from legacy.backup_config.backup import run_backup
from legacy.lib.utils import collect_devices_data
from legacy.lib.snapshot import take_snapshot
from legacy.lib.compare import compare
from inventory.lib.path import get_data_dir

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


def slow_print(message, style="green"):
    """Show a spinner while 'launching'"""
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[{style}]{message}[/{style}]"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("", total=100)
        for _ in range(100):
            progress.advance(task)
            time.sleep(0.01)


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
    [bold]1.[/bold] Backup Device Configurations

    [bold]2.[/bold] Take Snapshot and Health Check

    [bold]3.[/bold] Compare Snapshot

    [bold]4.[/bold] Mantools Online
    
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
    base_dir = get_data_dir()
    while True:
        print_header()
        show_menu()

        prompt_text = Text("\nEnter your choice: ", style="bold grey37")
        choice = console.input(prompt_text).strip().lower()

        if choice == "1":
            slow_print("Launching Backup Config Tools...", style="green")
            run_backup(base_dir)
            pause()

        elif choice == "2":
            slow_print("⏳ Taking snapshots and health check...", style="green")            
            take_snapshot(base_dir)
            pause()

        elif choice == "3":
            slow_print("🔍  Comparing snapshots...", style="green")   
            compare(base_dir)
            pause()

        elif choice == "4":
            slow_print("⏳ Collecting log for mantools online...", style="green")               
            collect_devices_data(base_dir)
            pause()

        elif choice == "q":
            slow_print("Exit Legacy Tools...", style="green")               
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
