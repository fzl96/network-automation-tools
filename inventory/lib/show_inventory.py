#!/usr/bin/env python3
import csv


INVENTORY_FILE = "inventory.csv"
def show_inventory():
    print("\nCurrent Device Inventory")
    try:
        with open(INVENTORY_FILE, "r") as csvfile:
            reader = csv.reader(csvfile, delimiter=";")
            print(f"{'Hostname':<20} {'IP':<20} {'OS Type':<10} {'Username':<15} {'Password (encrypted)'}")
            print("-" * 80)

            for row in reader:
                if len(row) >= 5:
                    print(f"{row[0]:<20} {row[1]:<20} {row[2]:<10} {row[3]:<15} {row[4]}")
    except FileNotFoundError:
        print("Inventory not found.")