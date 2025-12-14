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
from rich.text import Text
from rich.prompt import Prompt
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn

from aci import main_aci
from legacy import main_legacy
from legacy.customer_context import set_customer_name
from inventory import main_inventory
from sp_tools import main_sp

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

def resource_path(relative_path):
    """Get the absolute path to a resource, works with PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        # _MEIPASS is the temp folder PyInstaller extracts files into
        return Path(sys._MEIPASS) / relative_path # type: ignore
    return Path(relative_path)

def print_colored_logo():
    """Print the MSI logo in red from a text file"""
    logo_file = resource_path("assets/msi_logo.txt")
    red_code = "\033[1;31m"  # Bright red
    reset_code = "\033[0m"
    width = get_terminal_width()

    try:
        if logo_file.exists():
            with open(logo_file, "r", encoding="utf-8") as file:
                content = file.read()
                for line in content.splitlines():
                    print(f"{red_code}{line}{reset_code}".center(width))
            return True
        else:
            print(f"⚠️ Logo file not found: {logo_file}")
    except Exception as e:
        print(f"⚠️ Error loading logo: {e}")

    return False


def print_header():
    """Display header with colored logo and big title"""
    clear_screen()
    width = get_terminal_width()

    # Print MSI logo, fallback to text
    if not print_colored_logo():
        print("=" * width)
        print("MASTERSYSTEM INFOTAMA".center(width))
        print("=" * width)

    print()  # spacing

    darkgray = "\033[90m"
    reset = "\033[0m"

    ascii_title = pyfiglet.figlet_format("MANTOOLS", font="small")

    for line in ascii_title.splitlines():
        print(f"{darkgray}{line.center(width)}{reset}")

    print()  # spacing

    
def print_menu():
    console.print("\n")

    menu_text = """    
[bold]1.[/bold] Device Inventory
    
[bold]2.[/bold] ACI Tools

[bold]3.[/bold] Legacy Tools (IOS,IOS-XE and NX-OS) 

[bold]4.[/bold] SP Tools (IOS-XR)

[bold]q.[/bold] Exit
"""
    console.print(
        Panel(
            menu_text,
            title="🧰 Available Tools",
            title_align="left",
            border_style="grey37",
            padding=(1, 2),
        )
    )

# ============================================================
# Main Control
# ============================================================

def main():
    while True:
        print_header() 
        print_menu() 
        prompt_text = Text("\nEnter your choice: ", style="bold grey37")
        choice = console.input(prompt_text).strip().lower()

        
        if choice == "1":
            slow_print("Launching Inventory Tools...", style="green")
            main_inventory.main()
            
        elif choice == "2":
            slow_print("Launching ACI Tools...", style="green")
            main_aci.main()

        elif choice == "3":
            slow_print("Launching Legacy Tools...", style="green")
            main_legacy.main()

        elif choice == "4":
            slow_print("Launching SP Tools...", style="green")
            main_sp.main()

        elif choice == "q":
            slow_print("Exit System...", style="green")
            time.sleep(0.3)
            print("✅ System exit complete. Goodbye! 👋")
            sys.exit(0)

        else:
            print("\n❌ Invalid selection. Please try again.")
            pause()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    try:
        print_header()       
        # Instructions with proper formatting
        console.print("\n")
        console.print(
            Panel.fit(
                "[bold red]📋 Customer Name Requirements[/bold red]\n\n"
                "• Must be a single word\n"
                "• Contain only letters (A-Z, a-z)\n"
                "• No symbols or numbers allowed",
                border_style="grey37",
                padding=(1, 2)
            )
        )
        
        console.print("\n")

        while True:
            try:
                 # Prompt for customer name
                name = Prompt.ask(
                    "[bold grey37]Enter Customer Name[/bold grey37]",
                    default="",
                    show_default=False
                ).strip()
                
                set_customer_name(name)
                
                # Success message
                console.print(f"\n✅ [bold green]Customer '{name}' registered successfully![/bold green]\n")
                break
                
            except ValueError as e:
                console.print(f"\n❌ [bold red]Error:[/bold red] {e}")
                console.print("[yellow]Please try again...[/yellow]\n")
                console.rule(style="yellow")

        # Run main program
        main()
        
    except KeyboardInterrupt:
        console.print("\n\n⚠️  [yellow]Interrupted by user. Exiting gracefully...[/yellow]")
        sys.exit(0)
