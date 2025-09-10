#!/usr/bin/env python3
"""
Complete pipeline for generating and fixing Meshtastic node pages
This script runs all the necessary steps to generate and fix node pages:
1. Collect telemetry data (using meshtastic_telemetry_logger.py)
2. Generate plots and dashboards (using plot_meshtastic.py)
3. Fix duplicate Node ID issues (using node_page_updater.py)
4. Enhance metric visualization with battery progress bars and color coding (using enhance_node_visualizations.py)
5. Update example nodes with realistic data (using add_battery_to_examples.py)

This provides a single command to run the complete pipeline for convenience.
"""

import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle the result"""
    print(f"\n[STEP] {description}")
    print(f"[INFO] Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print(f"[SUCCESS] {description} completed successfully")
            return True
        else:
            print(f"[ERROR] {description} failed with code {result.returncode}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to execute command: {e}")
        return False

def run_pipeline(args):
    """Run the complete pipeline for Meshtastic node pages"""
    success = True
    
    # Step 1: Collect telemetry data if requested
    if args.collect:
        collect_cmd = ["python3", "meshtastic_telemetry_logger.py"]
        
        # Add additional arguments for collection
        if args.serial:
            collect_cmd.extend(["--serial", args.serial])
            
        if args.all_nodes:
            collect_cmd.append("--all-nodes")
        elif args.nodes:
            collect_cmd.extend(["--nodes"] + args.nodes)
            
        if args.once:
            collect_cmd.append("--once")
            
        # Always include plot flag for immediate plotting
        collect_cmd.append("--plot")
        
        # Run the collection command
        if not run_command(collect_cmd, "Collect telemetry data"):
            success = False
            print("[WARN] Telemetry collection failed, but continuing with pipeline")
    
    # Step 2: Generate plots and dashboards
    if args.skip_plot and not args.collect:
        print("\n[STEP] Generate plots and dashboards (SKIPPED)")
    else:
        # Only run plot_meshtastic.py if we didn't include --plot in the collection command
        if not args.collect:
            plot_cmd = [
                "python3", "plot_meshtastic.py",
                "--telemetry", args.telemetry,
                "--traceroute", args.traceroute,
                "--outdir", args.outdir
            ]
            
            if args.force:
                plot_cmd.append("--force")
                
            if not run_command(plot_cmd, "Generate plots and dashboards"):
                success = False
                print("[WARN] Plot generation failed, but continuing with fixes")
    
    # Step 3: Fix duplicate Node ID and enhance metrics
    if Path("node_page_updater.py").exists():
        fix_cmd = ["python3", "node_page_updater.py", "--fix-all", "--output-dir", args.outdir]
        if not run_command(fix_cmd, "Fix duplicate Node ID and enhance metrics"):
            success = False
            print("[WARN] Node page fixes with node_page_updater.py failed")
    elif Path("fix_all_node_pages.py").exists():
        # Fall back to old script if available
        fix_cmd = ["python3", "fix_all_node_pages.py", args.outdir]
        if not run_command(fix_cmd, "Fix and enhance node pages (legacy)"):
            success = False
            print("[WARN] Node page fixes with legacy script failed")
    else:
        print("[WARN] No node page fix scripts found")
        success = False
    
    # Report overall success or failure
    if success:
        print("\n[SUCCESS] Complete pipeline executed successfully")
        print(f"[INFO] Results available in {args.outdir} directory")
    else:
        print("\n[WARN] Pipeline completed with some failures")
        
    return success

def main():
    """Parse arguments and run pipeline"""
    parser = argparse.ArgumentParser(
        description="Complete pipeline for generating and fixing Meshtastic node pages")
    
    # Collection arguments
    parser.add_argument("--collect", action="store_true", 
                        help="Collect telemetry data before generating plots")
    parser.add_argument("--serial", help="Serial device path for collection")
    parser.add_argument("--all-nodes", action="store_true", 
                        help="Collect data from all nodes")
    parser.add_argument("--nodes", nargs="+", 
                        help="List of specific node IDs to collect data from")
    parser.add_argument("--once", action="store_true", 
                        help="Collect data only once, not continuously")
    
    # Plot arguments
    parser.add_argument("--skip-plot", action="store_true", 
                        help="Skip plot generation if collection is not requested")
    parser.add_argument("--telemetry", default="telemetry.csv", 
                        help="Path to telemetry CSV file")
    parser.add_argument("--traceroute", default="traceroute.csv", 
                        help="Path to traceroute CSV file")
    parser.add_argument("--outdir", default="plots", 
                        help="Output directory for plots and dashboards")
    parser.add_argument("--force", action="store_true", 
                        help="Force regeneration of all plots")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.collect:
        if not (args.all_nodes or args.nodes):
            print("[ERROR] Must specify --all-nodes or --nodes when using --collect")
            return 1
        if not args.once:
            print("[WARN] No --once flag provided; will collect data continuously")
            return 1
    
    # Check if node_page_updater.py or fix_all_node_pages.py exists
    if not (Path("node_page_updater.py").exists() or Path("fix_all_node_pages.py").exists()):
        print("[ERROR] Neither node_page_updater.py nor fix_all_node_pages.py found")
        return 1
    
    # Run the pipeline
    if run_pipeline(args):
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
