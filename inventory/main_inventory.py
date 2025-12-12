#!/usr/bin/env python3
import sys
import os
import time
import os
import pyfiglet
import shutil
import getpass

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

from inventory.lib.credential_manager import save_credentials, load_credentials
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
    [bold]1.[/bold] Save Default Credentials Securely

    [bold]2.[/bold] Create and Update Device Inventory

    [bold]3.[/bold] Show Inventory list

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

        prompt_text = Text("\nEnter your choice: ", style="bold grey37")
        choice = console.input(prompt_text).strip().lower()

        if choice == "1":
            slow_print("🔐 Saving credentials securely...", style="green")
            username = input("Enter username: ").strip()
            password = getpass.getpass("Enter Password (default hidden): ")
            save_credentials("default", username, password)
            slow_print("✅ Credentials saved successfully!")
            pause()

        elif choice == "2":
            username, password = load_credentials()
            if not username or not password:
                console.print("[yellow]No saved credentials found[/yellow]")
                slow_print("🔐 Saving credentials securely...", style="green")
                username = input("Enter username: ").strip()
                password = getpass.getpass("Enter Password (default hidden): ")
                save_credentials("default", username, password)
                slow_print("✅ Default Credentials saved successfully!")

                pause()
                continue
            slow_print("📋 Creating or updating inventory...", style="green")
            create_inventory(username, password)
            pause()

        elif choice == "3":
            slow_print("📄 Displaying inventory list...", style="green")
            show_inventory()
            pause()


        elif choice == "q":
            slow_print("Exit Inventory...", style="green")
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
