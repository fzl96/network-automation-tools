#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import pyfiglet
import shutil
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from sp_tools.Atlas.Atlas_10 import interactive_main as run_atlas
from sp_tools.CRCell.CRC_Cell_15 import interactive_main as run_crcell
from sp_tools.Snipe.snipe_R import interactive_main as run_snipe
from sp_tools.Xray.xray_8 import interactive_main as run_xray
console = Console()

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

    ascii_title = pyfiglet.figlet_format("SP TOOLS", font="standard")

    for line in ascii_title.splitlines():
        print(f"{red}{line.center(width)}{reset}")

    print()  # spacing


def show_menu():
    console.print("\n")
    menu_text = """
    [bold]1.[/bold] Atlas_v1

    [bold]2.[/bold] CRCell_v1

    [bold]3.[/bold] Snipe_v1

    [bold]4.[/bold] Xray_v1

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
    while True:
        print_header()
        show_menu()
        green = "\033[32m"
        reset = "\033[0m"

        choice = input("\nSelect an option (1-4 or q): ").strip().lower()

        if choice == "1":
            run_atlas()

        elif choice == "2":
            run_crcell()

        elif choice == "3":
            run_snipe()

        elif choice == "4":
            run_xray()

        elif choice == "q":
            slow_print("Exit SP Tools...", style="green")  
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