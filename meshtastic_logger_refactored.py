#!/usr/bin/env python3
"""
Refactored Meshtastic telemetry & traceroute logger.
- Clean separation of concerns using core modules
- Simplified main orchestration logic
- Better error handling and validation
- Modular design for easier maintenance
"""
import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from core import (
    discover_all_nodes, collect_nodes_detailed, normalize_node_id,
    collect_telemetry_batch, collect_traceroute_batch,
    setup_telemetry_csv, setup_traceroute_csv,
    iso_now, append_row
)


class MeshtasticLogger:
    """Main Meshtastic telemetry and traceroute logger class."""
    
    def __init__(self, args):
        self.args = args
        self.stop_requested = False
        
        # Setup file paths
        self.tele_csv = Path(args.output)
        self.trace_csv = Path(args.trace_output)
        self.plot_outdir = Path(args.plot_outdir)
        self.nodes_json_path = self.plot_outdir / "nodes_data.json"
        
        # Node tracking data
        self.all_nodes = {}
        self.node_seen_counts = {}
        self.node_first_seen = {}
        self.node_last_seen = {}
        self.total_tries = 0
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Setup output directories and CSV files
        self._setup_output_files()
        self._load_node_tracking_data()
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        print(f"\n[INFO] Received signal {signum}, stopping gracefully...", file=sys.stderr)
        self.stop_requested = True
    
    def _setup_output_files(self):
        """Setup output directories and CSV files with proper headers."""
        # Ensure output directory exists
        self.plot_outdir.mkdir(parents=True, exist_ok=True)
        
        # Setup CSV files
        setup_telemetry_csv(self.tele_csv)
        if not self.args.no_trace:
            setup_traceroute_csv(self.trace_csv)
    
    def _load_node_tracking_data(self):
        """Load existing node tracking data from JSON file."""
        if self.nodes_json_path.exists():
            try:
                with open(self.nodes_json_path, 'r') as f:
                    data = json.load(f)
                    self.all_nodes = data.get('all_nodes', {})
                    self.node_seen_counts = data.get('node_seen_counts', {})
                    self.node_first_seen = data.get('node_first_seen', {})
                    self.node_last_seen = data.get('node_last_seen', {})
                    self.total_tries = data.get('total_tries', 0)
                print(f"[INFO] Loaded tracking data for {len(self.all_nodes)} nodes")
            except Exception as e:
                print(f"[WARN] Could not load node tracking data: {e}", file=sys.stderr)
    
    def _save_node_tracking_data(self):
        """Save node tracking data to JSON file."""
        try:
            with open(self.nodes_json_path, 'w') as f:
                json.dump({
                    'all_nodes': self.all_nodes,
                    'node_seen_counts': self.node_seen_counts,
                    'node_first_seen': self.node_first_seen,
                    'node_last_seen': self.node_last_seen,
                    'total_tries': self.total_tries
                }, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save node data: {e}", file=sys.stderr)
    
    def _update_node_tracking(self, nodes: List[dict]):
        """Update node tracking information."""
        current_ts = iso_now()
        
        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue
            
            # Update counters and timestamps
            self.node_seen_counts[node_id] = self.node_seen_counts.get(node_id, 0) + 1
            
            if node_id not in self.node_first_seen:
                self.node_first_seen[node_id] = current_ts
            self.node_last_seen[node_id] = current_ts
            
            # Store node data
            self.all_nodes[node_id] = node
    
    def _get_target_nodes(self) -> List[str]:
        """Get the list of nodes to collect data from."""
        if self.args.all_nodes:
            discovered = discover_all_nodes(self.args.serial)
            print(f"[INFO] Auto-discovered {len(discovered)} nodes")
            return discovered
        else:
            return [normalize_node_id(node) for node in self.args.nodes]
    
    def _collect_and_log_telemetry(self, target_nodes: List[str], cycle_ts: str):
        """Collect and log telemetry data for target nodes."""
        print(f"[INFO] Collecting telemetry from {len(target_nodes)} nodes...")
        
        telemetry_data = collect_telemetry_batch(
            target_nodes, 
            self.args.serial, 
            timeout=30
        )
        
        # Log telemetry to CSV
        for node_id, tele in telemetry_data.items():
            append_row(self.tele_csv, [
                cycle_ts, node_id,
                tele.get("battery_pct", ""),
                tele.get("voltage_v", ""),
                tele.get("channel_util_pct", ""),
                tele.get("air_tx_pct", ""),
                tele.get("uptime_s", "")
            ])
            
            # Update node data
            if node_id in self.all_nodes:
                self.all_nodes[node_id].update(tele)
        
        return telemetry_data
    
    def _collect_and_log_traceroute(self, target_nodes: List[str], cycle_ts: str):
        """Collect and log traceroute data for target nodes."""
        if self.args.no_trace:
            return {}
        
        print(f"[INFO] Running traceroutes to {len(target_nodes)} nodes...")
        
        traceroute_data = collect_traceroute_batch(
            target_nodes,
            self.args.serial,
            timeout=30
        )
        
        # Log traceroute to CSV
        for node_id, routes in traceroute_data.items():
            # Log forward hops
            for i, (src, dst, db) in enumerate(routes.get("forward", [])):
                append_row(self.trace_csv, [cycle_ts, node_id, "forward", i, src, dst, db])
            
            # Log backward hops  
            for i, (src, dst, db) in enumerate(routes.get("back", [])):
                append_row(self.trace_csv, [cycle_ts, node_id, "backward", i, src, dst, db])
        
        return traceroute_data
    
    def _run_plotting(self):
        """Run the plotting script to generate visualizations."""
        if not self.args.plot:
            return
        
        try:
            plot_cmd = [
                "python3", "plot_meshtastic.py",
                "--telemetry", str(self.tele_csv),
                "--traceroute", str(self.trace_csv),
                "--outdir", str(self.plot_outdir)
            ]
            
            if self.args.regenerate_charts:
                plot_cmd.append("--regenerate-charts")
                
            if self.args.preserve_history:
                plot_cmd.append("--preserve-history")
            
            print("[INFO] Running plotting script...")
            subprocess.run(plot_cmd, check=True)
            print("[INFO] Plotting completed successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Plotting failed: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Unexpected plotting error: {e}", file=sys.stderr)
    
    def run_cycle(self):
        """Run a single data collection cycle."""
        cycle_ts = iso_now()
        self.total_tries += 1
        
        print(f"\n[INFO] === Cycle {self.total_tries} at {cycle_ts} ===")
        
        # Discover all nodes for tracking
        all_discovered_nodes = collect_nodes_detailed(self.args.serial)
        self._update_node_tracking(all_discovered_nodes)
        
        # Get target nodes for data collection
        target_nodes = self._get_target_nodes()
        if not target_nodes:
            print("[WARN] No target nodes found for data collection")
            return
        
        print(f"[INFO] Target nodes: {target_nodes}")
        
        # Collect telemetry data
        telemetry_data = self._collect_and_log_telemetry(target_nodes, cycle_ts)
        
        # Collect traceroute data
        traceroute_data = self._collect_and_log_traceroute(target_nodes, cycle_ts)
        
        # Save node tracking data
        self._save_node_tracking_data()
        
        # Run plotting if requested
        self._run_plotting()
        
        print(f"[INFO] Cycle completed. Telemetry: {len(telemetry_data)} nodes, "
              f"Traceroute: {len(traceroute_data)} nodes")
    
    def run(self):
        """Main execution loop."""
        print("[INFO] Starting Meshtastic telemetry logger")
        print(f"[INFO] Output: telemetry={self.tele_csv}, traceroute={self.trace_csv}")
        print(f"[INFO] Plots: {self.plot_outdir}")
        
        while not self.stop_requested:
            try:
                self.run_cycle()
                
                if self.args.once:
                    break
                
                # Sleep until next cycle
                print(f"[INFO] Sleeping for {self.args.interval} seconds...")
                for _ in range(int(self.args.interval * 10)):
                    if self.stop_requested:
                        break
                    time.sleep(0.1)
                    
            except KeyboardInterrupt:
                print("\n[INFO] Interrupted by user", file=sys.stderr)
                break
            except Exception as e:
                print(f"[ERROR] Unexpected error in cycle: {e}", file=sys.stderr)
                if self.args.once:
                    break
                # Continue running in interval mode
                
        print("[INFO] Meshtastic logger stopped")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Meshtastic telemetry & traceroute logger (refactored)")
    
    # Node selection
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--nodes", nargs="+", help="List of node IDs to monitor (e.g., !abc123 !def456)")
    group.add_argument("--all-nodes", action="store_true", help="Auto-discover and monitor all nodes")
    
    # Connection options
    parser.add_argument("--serial", help="Serial device path (e.g., /dev/ttyACM0)")
    
    # Output options
    parser.add_argument("--output", default="telemetry.csv", help="Telemetry CSV output file")
    parser.add_argument("--trace-output", default="traceroute.csv", help="Traceroute CSV output file")
    parser.add_argument("--plot-outdir", default="plots", help="Output directory for plots and HTML")
    
    # Execution options
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=float, default=300, help="Interval between cycles in seconds")
    
    # Feature toggles
    parser.add_argument("--no-trace", action="store_true", help="Disable traceroute collection")
    parser.add_argument("--plot", action="store_true", help="Generate plots after data collection")
    parser.add_argument("--regenerate-charts", action="store_true", help="Force regeneration of all charts")
    parser.add_argument("--preserve-history", action="store_true", help="Create timestamped directories and preserve history")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Validate arguments
    if not args.all_nodes and not args.nodes:
        print("[ERROR] Must specify either --nodes or --all-nodes", file=sys.stderr)
        return 1
    
    try:
        logger = MeshtasticLogger(args)
        logger.run()
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to start logger: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())