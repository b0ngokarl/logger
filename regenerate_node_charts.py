#!/usr/bin/env python3
"""
Regenerate node charts for specific nodes to fix display issues with:
- Channel utilization
- Air TX
- Battery visualization
- Fix duplicate Node ID display issues
- Enhance metric visualization

This script calls plot_meshtastic.py to regenerate charts and then applies
the node page fixes and enhancements.
"""
import subprocess
import argparse
from pathlib import Path

def regenerate_node_charts(node_ids, plots_dir="plots", telemetry_csv="telemetry.csv", apply_fixes=True):
    """
    Regenerate charts for specific nodes
    
    Args:
        node_ids: List of node IDs to regenerate charts for
        plots_dir: Directory containing the plots
        telemetry_csv: Path to the telemetry CSV file
        apply_fixes: Whether to apply fixes and enhancements to node pages
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Build the command to regenerate charts
        cmd = [
            "python3", "plot_meshtastic.py",
            "--telemetry", telemetry_csv,
            "--outdir", plots_dir,
            "--force"
        ]
        
        # Add node IDs to the command
        for node_id in node_ids:
            cmd.extend(["--node", node_id])
            
        print(f"[INFO] Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print(f"[INFO] Successfully regenerated charts for {len(node_ids)} nodes")
            
            # Apply fixes and enhancements if requested
            if apply_fixes and Path("fix_all_node_pages.py").exists():
                print("[INFO] Applying fixes and enhancements to node pages")
                fix_cmd = ["python3", "fix_all_node_pages.py", plots_dir]
                subprocess.run(fix_cmd, check=True)
            
            return True
        else:
            print("[ERROR] Failed to regenerate charts")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def main():
    """Main function to regenerate charts for specific nodes."""
    parser = argparse.ArgumentParser(description="Regenerate node charts for specific nodes.")
    parser.add_argument("--nodes", nargs="+", default=[], 
                        help="List of node IDs to regenerate charts for (e.g., !2df67288)")
    parser.add_argument("--all", action="store_true", help="Regenerate charts for all nodes")
    parser.add_argument("--no-fixes", action="store_true", help="Skip applying fixes and enhancements")
    parser.add_argument("--outdir", default="plots", help="Output directory for plots")
    parser.add_argument("--telemetry", default="telemetry.csv", help="Path to the telemetry CSV file")
    args = parser.parse_args()

    # Default node IDs with issues as mentioned
    default_nodes = ["2df67288", "277db5ca", "2c9e092b", "75e98c18", "849c4818", "ba656304"]
    
    if not args.nodes and not args.all:
        print("[INFO] Using default node list from known issues")
        nodes = default_nodes
    elif args.all:
        print("[INFO] Will regenerate charts for ALL nodes")
        # Get all node IDs from the output directory
        try:
            plots_dir = Path(args.outdir)
            node_dirs = [d for d in plots_dir.glob('node_*') if d.is_dir()]
            nodes = [d.name.replace('node_', '') for d in node_dirs]
            if not nodes:
                print("[WARN] No node directories found in plots directory")
                return
        except Exception as e:
            print(f"[ERROR] Error finding node directories: {e}")
            return
    else:
        # Clean node IDs from command line arguments
        nodes = [node.strip('!') for node in args.nodes]
    
    # Add ! prefix to node IDs for the command
    node_ids = [f"!{node}" for node in nodes]
    print(f"[INFO] Regenerating charts for {len(node_ids)} nodes: {', '.join(node_ids)}")
    
    # Regenerate charts and apply fixes
    regenerate_node_charts(node_ids, args.outdir, args.telemetry, not args.no_fixes)
    
    print(f"\n[INFO] Charts regenerated. You can view them in the {args.outdir} directory.")
    print("[INFO] Updated node pages should now display correct metrics and fixed layout.")

if __name__ == "__main__":
    main()
