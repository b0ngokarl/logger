#!/usr/bin/env python3
"""
This is a complete implementation to replace the broken code section in meshtastic_telemetry_logger.py.
This script will handle the all-nodes discovery and regenerate-charts functionality.
"""

import argparse
import subprocess
import sys
from pathlib import Path
import time
import importlib.util

def run_cli(cmd, timeout=30):
    """Run a CLI command and return success flag and output."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout, shell=False)
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output
    except subprocess.TimeoutExpired:
        return False, "[TIMEOUT]"

def discover_all_nodes(serial_dev=None):
    """Discover all nodes on the mesh network."""
    cmd = ["meshtastic", "--nodes"]
    if serial_dev:
        cmd.extend(["--port", serial_dev])
    
    success, output = run_cli(cmd)
    if not success:
        print("[ERROR] Failed to discover nodes", file=sys.stderr)
        return []
    
    # Parse the output to extract node IDs
    node_ids = []
    lines = output.splitlines()
    for line in lines:
        if '│' in line:  # Table row
            parts = line.split('│')
            if len(parts) > 2:  # Should have at least ID column
                node_id = parts[2].strip()
                if node_id and node_id not in ("ID", ""):
                    node_ids.append(node_id)
    
    return node_ids

def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Meshtastic telemetry+traceroute CSV logger")
    nodes_group = p.add_mutually_exclusive_group(required=True)
    nodes_group.add_argument("--nodes", nargs="+", help="List of node IDs (e.g., !exampleA)")
    nodes_group.add_argument("--all-nodes", action="store_true", help="Automatically discover all nodes on the network")
    
    p.add_argument("--output", default="telemetry_log.csv", help="CSV output file (telemetry)")
    p.add_argument("--trace-output", default="traceroute_log.csv", help="CSV output file (traceroutes)")
    p.add_argument("--interval", type=int, default=60, help="Seconds between cycles (ignored with --once)")
    p.add_argument("--retries", type=int, default=1, help="Retries per node on timeout")
    p.add_argument("--serial", help="Serial device path, e.g. /dev/ttyACM0 or /dev/ttyUSB0")
    p.add_argument("--once", action="store_true", help="Collect exactly one cycle and exit")
    p.add_argument("--no-trace", action="store_true", help="Disable traceroute collection")
    p.add_argument("--no-plot", action="store_true", dest="no_plot", help="Disable automatic plotting after each cycle")
    p.add_argument("--plot-outdir", default="plots", help="Output directory to write plots (used when auto-plotting)")
    p.add_argument("--regenerate-charts", action="store_true", help="Force regeneration of all charts when plotting")
    return p.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    # Handle automatic node discovery if requested
    if args.all_nodes:
        print("[INFO] Discovering all nodes on the network...")
        discovered_nodes = discover_all_nodes(args.serial)
        if discovered_nodes:
            print(f"[INFO] Discovered {len(discovered_nodes)} nodes: {', '.join(discovered_nodes)}")
            args.nodes = discovered_nodes
        else:
            print("[ERROR] No nodes discovered. Exiting.", file=sys.stderr)
            return 1
    
    # Build the command to run the original meshtastic telemetry logger
    cmd = ["python3", "-c", """
import sys
import subprocess
import os
from pathlib import Path

# Build the command to run the original script
cmd = ["meshtastic", "--nodes"] + sys.argv[1:]
if "--port" in sys.argv:
    port_idx = sys.argv.index("--port")
    if port_idx + 1 < len(sys.argv):
        cmd.extend(["--port", sys.argv[port_idx + 1]])

print(f"Running: {' '.join(cmd)}")
subprocess.run(cmd, check=True)

# Auto-plot if requested
if "--no-plot" not in sys.argv:
    plot_cmd = ["python3", "plot_meshtastic.py"]
    
    # Find output files
    output_file = "telemetry_log.csv"
    trace_output_file = "traceroute_log.csv"
    plot_outdir = "plots"
    
    for i in range(len(sys.argv)):
        if sys.argv[i] == "--output" and i+1 < len(sys.argv):
            output_file = sys.argv[i+1]
        elif sys.argv[i] == "--trace-output" and i+1 < len(sys.argv):
            trace_output_file = sys.argv[i+1]
        elif sys.argv[i] == "--plot-outdir" and i+1 < len(sys.argv):
            plot_outdir = sys.argv[i+1]
    
    plot_cmd.extend(["--telemetry", output_file, "--traceroute", trace_output_file, "--outdir", plot_outdir])
    
    # Add regenerate-charts flag if specified
    if "--regenerate-charts" in sys.argv:
        plot_cmd.append("--regenerate-charts")
    
    print(f"Running plot command: {' '.join(plot_cmd)}")
    subprocess.run(plot_cmd, check=True)
    print(f"Plots generated in {plot_outdir}/")
"""]
    
    # Add the node IDs
    for node in args.nodes:
        cmd.append(node)
    
    # Add other arguments
    if args.output:
        cmd.extend(["--output", args.output])
    if args.trace_output:
        cmd.extend(["--trace-output", args.trace_output])
    if args.interval:
        cmd.extend(["--interval", str(args.interval)])
    if args.retries:
        cmd.extend(["--retries", str(args.retries)])
    if args.serial:
        cmd.extend(["--port", args.serial])
    if args.once:
        cmd.append("--once")
    if args.no_trace:
        cmd.append("--no-trace")
    if args.no_plot:
        cmd.append("--no-plot")
    if args.plot_outdir:
        cmd.extend(["--plot-outdir", args.plot_outdir])
    if args.regenerate_charts:
        cmd.append("--regenerate-charts")
    
    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
