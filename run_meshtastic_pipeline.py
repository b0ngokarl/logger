#!/usr/bin/env python3
"""
Run the complete Meshtastic telemetry collection pipeline:
1. Run data collection
2. Fix node information display issues
3. Regenerate charts for problematic nodes

This script serves as a convenient wrapper to ensure consistency in node displays.
"""
import os
import sys
import subprocess
import argparse
from datetime import datetime

def log_info(msg):
    """Print an info log message with timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INFO] {now} {msg}")

def log_warn(msg):
    """Print a warning log message with timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[WARN] {now} {msg}")

def log_error(msg):
    """Print an error log message with timestamp."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ERROR] {now} {msg}", file=sys.stderr)

def run_command(cmd, description=None):
    """Run a command and log its execution."""
    if description:
        log_info(f"{description}: {' '.join(cmd)}")
    else:
        log_info(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    """Main function to run the complete pipeline."""
    parser = argparse.ArgumentParser(description="Run the Meshtastic telemetry collection pipeline.")
    parser.add_argument("--nodes", nargs="+", help="List of node IDs to collect telemetry for (e.g., !2df67288)")
    parser.add_argument("--all-nodes", action="store_true", help="Collect telemetry for all nodes")
    parser.add_argument("--once", action="store_true", help="Run data collection only once (otherwise runs continuously)")
    parser.add_argument("--no-plot", action="store_true", help="Skip plot generation")
    parser.add_argument("--fix-nodes", nargs="+", default=[], help="List of node IDs to regenerate charts for")
    
    args = parser.parse_args()
    
    # Verify we have the necessary scripts
    scripts = ["meshtastic_telemetry_logger.py", "plot_meshtastic.py"]
    for script in scripts:
        if not os.path.exists(script):
            log_error(f"Required script {script} not found")
            return 1
    
    # Step 1: Run the telemetry collection
    collection_cmd = ["python3", "meshtastic_telemetry_logger.py"]
    
    if args.all_nodes:
        collection_cmd.append("--all-nodes")
    elif args.nodes:
        collection_cmd.extend(["--nodes"] + args.nodes)
    else:
        log_warn("No nodes specified, will use defaults or all nodes")
    
    if args.once:
        collection_cmd.append("--once")
    
    # Run the collection
    log_info("Starting telemetry collection")
    if not run_command(collection_cmd, "Running telemetry collection"):
        log_error("Telemetry collection failed")
        return 1
    
    # Step 2: Generate plots unless disabled
    if not args.no_plot:
        plot_cmd = [
            "python3", "plot_meshtastic.py",
            "--telemetry", "telemetry.csv",
            "--traceroute", "traceroute.csv",
            "--outdir", "plots"
        ]
        
        # Add nodes to fix/regenerate if specified
        fix_nodes = args.fix_nodes or [
            "2df67288", "277db5ca", "2c9e092b", "75e98c18", "849c4818", "ba656304"
        ]
        
        if fix_nodes:
            # Strip '!' prefix if present for consistency
            fix_nodes = [node.lstrip('!') for node in fix_nodes]
            plot_cmd.extend(["--regenerate-specific-nodes"] + fix_nodes)
            
        log_info("Generating plots and fixing node charts")
        if not run_command(plot_cmd, "Generating plots"):
            log_error("Plot generation failed")
            return 1
    
    log_info("Pipeline completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
