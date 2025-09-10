#!/usr/bin/env python3
"""
Example script demonstrating the use of the all-nodes and regenerate-charts features
"""

import subprocess
import sys

def print_section(title):
    """Print a section title"""
    print("\n" + "=" * 60)
    print(f" {title} ".center(60))
    print("=" * 60)

def run_command(cmd):
    """Run a command and print its output"""
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}", file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with exit code {e.returncode}", file=sys.stderr)
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}", file=sys.stderr)
        return False

def main():
    """Main function"""
    print_section("Meshtastic Telemetry Logger with All-Nodes Discovery")
    
    # Example 1: Discover all nodes and collect telemetry once
    print("Example 1: Discover all nodes and collect telemetry once")
    run_command([
        "python3", "meshtastic_telemetry_logger.py",
        "--all-nodes",
        "--once",
        "--output", "telemetry.csv",
        "--trace-output", "traceroute.csv",
        "--plot-outdir", "plots"
    ])
    
    # Example 2: Use with regenerate-charts flag
    print_section("Example 2: Force regeneration of all charts")
    run_command([
        "python3", "meshtastic_telemetry_logger.py",
        "--all-nodes",
        "--once",
        "--output", "telemetry.csv",
        "--trace-output", "traceroute.csv",
        "--plot-outdir", "plots",
        "--regenerate-charts"
    ])
    
    # Example 3: Run plotting with regenerate-charts only
    print_section("Example 3: Run plotting with regenerate-charts only")
    run_command([
        "python3", "plot_meshtastic.py",
        "--telemetry", "telemetry.csv",
        "--traceroute", "traceroute.csv",
        "--outdir", "plots",
        "--regenerate-charts"
    ])
    
    print_section("Done")
    print("You can now open plots/index.html to view the dashboards")
    print("Each node should have its own page in plots/node_<id>/index.html")

if __name__ == "__main__":
    main()
