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
from aci import main_aci
from legacy import main_legacy
from legacy.customer_context import set_customer_name
from inventory import main_inventory
from legacy.creds.credential_manager import save_credentials, load_credentials
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

def print_colored_logo():
    """Print the MSI logo in red from a text file"""
    logo_file = Path("assets/msi_logo.txt")
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
        green = "\033[32m"
        reset = "\033[0m"

        choice = input("\nEnter your choice: ").strip().lower()

        
        if choice == "1":
            slow_print(f"{green}{"\nLaunching Inventory Tools..."}{reset}")
            main_inventory.main()
            
        elif choice == "2":
            slow_print(f"{green}{"\nLaunching ACI Tools..."}{reset}")
            main_aci.main()

        elif choice == "3":
            slow_print(f"{green}{"\nLaunching Legacy Tools..."}{reset}")
            main_legacy.main()

        elif choice == "4":
            slow_print(f"{green}{"\nLaunching SP Tools..."}{reset}")
            main_sp.main()

        elif choice == "q":
            slow_print(f"{green}{"\nExit System..."}{reset}")
            time.sleep(0.3)
            print("✅ System exit complete. Goodbye! 👋")
            break

        else:
            print("\n❌ Invalid selection. Please try again.")
            pause()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    try:
        print_header()       
        green = "\033[32m"
        reset = "\033[0m"        
        slow_print(f"{green}{"\nPlease enter the Customer Name first..."}{reset}")
        set_customer_name(input(f"{green}{"Enter Customer Name: "}{reset}").strip())
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting gracefully...")
        sys.exit(0)
