#!/usr/bin/env python3
"""
Simple test script to demonstrate the functionality of the discover_all_nodes.py script
and plot_meshtastic.py with --regenerate-charts flag.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, check=False):
    """Run a command and print its output."""
    print(f"\nRunning: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, check=check)
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False, ""

def main():
    print("=" * 60)
    print(" Testing Node Discovery ".center(60))
    print("=" * 60)
    
    # First test: Run discover_all_nodes.py
    success, nodes_output = run_command(["python3", "discover_all_nodes.py"])
    if not success:
        print("Error running discover_all_nodes.py")
    
    # Second test: Run plot_meshtastic.py with --regenerate-charts
    print("\n" + "=" * 60)
    print(" Testing Plot Generation with Chart Regeneration ".center(60))
    print("=" * 60)
    
    # Check if example CSV files exist, use them if available
    telemetry_file = "telemetry.csv"
    if not Path(telemetry_file).exists():
        telemetry_file = "examples/telemetry_example.csv"
    
    traceroute_file = "traceroute.csv"
    if not Path(traceroute_file).exists():
        traceroute_file = "examples/traceroute_example.csv"
    
    cmd = [
        "python3", "plot_meshtastic.py",
        "--telemetry", telemetry_file,
        "--traceroute", traceroute_file,
        "--outdir", "plots",
        "--regenerate-charts"
    ]
    
    success, _ = run_command(cmd)
    if not success:
        print("Error running plot_meshtastic.py with --regenerate-charts")
        
    print("\n" + "=" * 60)
    print(" Done ".center(60))
    print("=" * 60)
    print("Open plots/index.html to view the generated dashboards.")

if __name__ == "__main__":
    main()
