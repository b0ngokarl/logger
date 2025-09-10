#!/usr/bin/env python3
"""
Automated Meshtastic Logger with Intelligent Scheduling

This script provides a fully automated "one-command" solution that:
- Automatically discovers nodes
- Collects telemetry and traceroute data continuously  
- Generates plots and dashboards automatically
- Handles node completion detection and triggered actions
- Provides real-time dashboard updates

Usage:
    # Complete automation - just run and forget
    python3 auto_meshtastic_logger.py
    
    # With custom settings
    python3 auto_meshtastic_logger.py --interval 300 --serial /dev/ttyACM0 --outdir monitoring
"""
import argparse
import json
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from core import (
    discover_all_nodes, collect_nodes_detailed, normalize_node_id,
    collect_telemetry_batch, collect_traceroute_batch,
    setup_telemetry_csv, setup_traceroute_csv,
    iso_now, append_row
)


class AutoMeshtasticLogger:
    """Intelligent automated Meshtastic logger with completion detection."""
    
    def __init__(self, args):
        self.args = args
        self.stop_requested = False
        
        # Setup file paths with timestamped directory structure
        base_dir = Path(args.outdir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = base_dir / f"run_{timestamp}"
        self.latest_link = base_dir / "latest"
        
        # Setup output structure
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Create or update "latest" symlink
        if self.latest_link.is_symlink():
            self.latest_link.unlink()
        self.latest_link.symlink_to(self.run_dir.name)
        
        self.tele_csv = self.run_dir / "telemetry.csv"
        self.trace_csv = self.run_dir / "traceroute.csv"
        self.plot_outdir = self.run_dir / "plots"
        self.stats_json = self.run_dir / "run_stats.json"
        
        # Node tracking and completion detection
        self.discovered_nodes: Set[str] = set()
        self.active_nodes: Set[str] = set()
        self.completed_nodes: Set[str] = set()
        self.node_last_seen: Dict[str, datetime] = {}
        self.node_telemetry_count: Dict[str, int] = {}
        self.node_completion_time: Dict[str, datetime] = {}
        
        # Collection statistics
        self.total_cycles = 0
        self.total_telemetry_collected = 0
        self.total_traceroutes = 0
        self.start_time = datetime.now()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize CSV files
        setup_telemetry_csv(self.tele_csv)
        setup_traceroute_csv(self.trace_csv)
        
        print(f"[INFO] Auto-logger initialized")
        print(f"[INFO] Output directory: {self.run_dir}")
        print(f"[INFO] Plots will be available at: {self.plot_outdir}")
        print(f"[INFO] Latest run accessible via: {self.latest_link}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[INFO] Received signal {signum}, shutting down gracefully...")
        self.stop_requested = True
    
    def _save_stats(self):
        """Save run statistics to JSON file."""
        stats = {
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now().isoformat(),
            "total_cycles": self.total_cycles,
            "total_telemetry_collected": self.total_telemetry_collected,
            "total_traceroutes": self.total_traceroutes,
            "discovered_nodes": list(self.discovered_nodes),
            "active_nodes": list(self.active_nodes),
            "completed_nodes": list(self.completed_nodes),
            "node_telemetry_counts": self.node_telemetry_count,
            "node_completion_times": {k: v.isoformat() for k, v in self.node_completion_time.items()}
        }
        
        try:
            with open(self.stats_json, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save stats: {e}", file=sys.stderr)
    
    def _discover_nodes(self) -> List[str]:
        """Discover nodes and update tracking."""
        print("[INFO] Discovering nodes...")
        nodes = discover_all_nodes(self.args.serial, timeout=30)
        
        # Update discovered nodes set
        new_nodes = set(nodes) - self.discovered_nodes
        if new_nodes:
            print(f"[INFO] Found {len(new_nodes)} new nodes: {', '.join(new_nodes)}")
            self.discovered_nodes.update(new_nodes)
        
        # Update active nodes (nodes seen recently)
        current_time = datetime.now()
        for node in nodes:
            self.node_last_seen[node] = current_time
            if node not in self.completed_nodes:
                self.active_nodes.add(node)
        
        return nodes
    
    def _check_node_completion(self, node: str) -> bool:
        """
        Check if a node should be considered 'completed' based on collection criteria.
        A node is completed if:
        1. It has been seen multiple times (min_telemetry_count)
        2. No new data for completion_timeout seconds
        """
        min_telemetry = self.args.min_telemetry_count
        timeout = timedelta(seconds=self.args.completion_timeout)
        current_time = datetime.now()
        
        # Check if node has enough telemetry data
        telemetry_count = self.node_telemetry_count.get(node, 0)
        if telemetry_count < min_telemetry:
            return False
        
        # Check if node hasn't been seen for a while
        last_seen = self.node_last_seen.get(node)
        if last_seen and (current_time - last_seen) > timeout:
            return True
        
        return False
    
    def _update_node_completion_status(self):
        """Update node completion status and trigger actions."""
        newly_completed = []
        
        for node in list(self.active_nodes):
            if self._check_node_completion(node):
                self.active_nodes.remove(node)
                self.completed_nodes.add(node)
                self.node_completion_time[node] = datetime.now()
                newly_completed.append(node)
        
        if newly_completed:
            print(f"[INFO] Nodes completed: {', '.join(newly_completed)}")
            
            # Trigger plotting for completed nodes
            if self.args.plot_on_completion:
                self._run_plotting()
    
    def _collect_cycle_data(self) -> bool:
        """
        Perform one complete data collection cycle.
        Returns True if any data was collected.
        """
        cycle_ts = iso_now()
        self.total_cycles += 1
        
        print(f"[INFO] === Collection Cycle {self.total_cycles} ===")
        
        # Discover current nodes
        current_nodes = self._discover_nodes()
        if not current_nodes:
            print("[WARN] No nodes discovered in this cycle")
            return False
        
        # Collect telemetry
        print(f"[INFO] Collecting telemetry from {len(current_nodes)} nodes...")
        telemetry_data = collect_telemetry_batch(current_nodes, self.args.serial, timeout=30)
        
        # Log telemetry to CSV
        telemetry_collected = 0
        for node_id, tele in telemetry_data.items():
            if tele:  # Only log if we got actual data
                append_row(self.tele_csv, [
                    cycle_ts, node_id,
                    # Basic device metrics
                    tele.get("battery_pct", ""),
                    tele.get("voltage_v", ""),
                    tele.get("channel_util_pct", ""),
                    tele.get("air_tx_pct", ""),
                    tele.get("uptime_s", ""),
                    # Environment sensors
                    tele.get("temperature_c", ""),
                    tele.get("humidity_pct", ""),
                    tele.get("pressure_hpa", ""),
                    tele.get("iaq", ""),
                    tele.get("lux", ""),
                    # Power monitoring
                    tele.get("current_ma", ""),
                    tele.get("ch1_voltage_v", ""),
                    tele.get("ch1_current_ma", ""),
                    tele.get("ch2_voltage_v", ""),
                    tele.get("ch2_current_ma", ""),
                    tele.get("ch3_voltage_v", ""),
                    tele.get("ch3_current_ma", ""),
                    tele.get("ch4_voltage_v", ""),
                    tele.get("ch4_current_ma", "")
                ])
                self.node_telemetry_count[node_id] = self.node_telemetry_count.get(node_id, 0) + 1
                telemetry_collected += 1
        
        self.total_telemetry_collected += telemetry_collected
        print(f"[INFO] Collected telemetry from {telemetry_collected} nodes")
        
        # Collect traceroute data if enabled
        traceroutes_collected = 0
        if not self.args.no_trace:
            print(f"[INFO] Running traceroutes to {len(current_nodes)} nodes...")
            traceroute_data = collect_traceroute_batch(current_nodes, self.args.serial, timeout=45)
            
            # Log traceroute to CSV
            for dest, traces in traceroute_data.items():
                for trace in traces:
                    append_row(self.trace_csv, [
                        cycle_ts,
                        trace.get("dest", dest),
                        trace.get("direction", ""),
                        trace.get("hop_index", ""),
                        trace.get("from", ""),
                        trace.get("to", ""),
                        trace.get("link_db", "")
                    ])
                    traceroutes_collected += 1
            
            self.total_traceroutes += traceroutes_collected
            print(f"[INFO] Collected {traceroutes_collected} traceroute hops")
        
        # Update node completion status
        self._update_node_completion_status()
        
        # Save statistics
        self._save_stats()
        
        return telemetry_collected > 0 or traceroutes_collected > 0
    
    def _run_plotting(self):
        """Generate plots and dashboards."""
        try:
            plot_cmd = [
                "python3", "plot_meshtastic.py",
                "--telemetry", str(self.tele_csv),
                "--traceroute", str(self.trace_csv),
                "--outdir", str(self.plot_outdir)
            ]
            
            if self.args.regenerate_charts:
                plot_cmd.append("--regenerate-charts")
            
            print("[INFO] Generating plots and dashboards...")
            result = subprocess.run(plot_cmd, check=True, capture_output=True, text=True)
            print("[INFO] Plots generated successfully")
            print(f"[INFO] Dashboard available at: {self.plot_outdir / 'index.html'}")
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Plotting failed: {e}", file=sys.stderr)
            if e.stdout:
                print(f"[ERROR] Stdout: {e.stdout}", file=sys.stderr)
            if e.stderr:
                print(f"[ERROR] Stderr: {e.stderr}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Unexpected plotting error: {e}", file=sys.stderr)
    
    def run(self):
        """Main execution loop with intelligent automation."""
        print(f"[INFO] Starting automated collection with {self.args.interval}s intervals")
        print(f"[INFO] Min telemetry per node: {self.args.min_telemetry_count}")
        print(f"[INFO] Node completion timeout: {self.args.completion_timeout}s")
        
        next_plot_time = datetime.now() + timedelta(seconds=self.args.plot_interval)
        
        while not self.stop_requested:
            try:
                # Perform data collection cycle
                collected_data = self._collect_cycle_data()
                
                # Generate plots periodically or when triggered
                current_time = datetime.now()
                if (current_time >= next_plot_time) or (collected_data and self.args.plot_every_cycle):
                    self._run_plotting()
                    next_plot_time = current_time + timedelta(seconds=self.args.plot_interval)
                
                # Print status
                active_count = len(self.active_nodes)
                completed_count = len(self.completed_nodes)
                print(f"[STATUS] Active nodes: {active_count}, Completed: {completed_count}, Total cycles: {self.total_cycles}")
                
                # Check if we should continue
                if self.args.stop_when_all_complete and active_count == 0 and completed_count > 0:
                    print("[INFO] All nodes completed, stopping as requested")
                    break
                
                # Sleep until next cycle
                print(f"[INFO] Waiting {self.args.interval}s until next cycle...")
                for i in range(int(self.args.interval)):
                    if self.stop_requested:
                        break
                    time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n[INFO] Interrupted by user")
                break
            except Exception as e:
                print(f"[ERROR] Cycle error: {e}", file=sys.stderr)
                time.sleep(5)  # Brief pause before retrying
        
        # Final plotting
        print("[INFO] Performing final plot generation...")
        self._run_plotting()
        
        # Save final statistics
        self._save_stats()
        
        print("[INFO] Automated logger stopped")
        print(f"[INFO] Final results in: {self.run_dir}")
        print(f"[INFO] Dashboard: {self.plot_outdir / 'index.html'}")


def main():
    parser = argparse.ArgumentParser(
        description="Automated Meshtastic Logger with Intelligent Completion Detection"
    )
    
    # Connection options
    parser.add_argument("--serial", help="Serial device path (e.g., /dev/ttyACM0)")
    
    # Output options
    parser.add_argument("--outdir", default="monitoring", 
                       help="Base output directory (run directories created inside)")
    
    # Collection timing
    parser.add_argument("--interval", type=int, default=300, 
                       help="Interval between collection cycles in seconds")
    parser.add_argument("--min-telemetry-count", type=int, default=3,
                       help="Minimum telemetry collections before considering node complete")
    parser.add_argument("--completion-timeout", type=int, default=1800,
                       help="Seconds of no data before marking node as complete")
    
    # Plotting options
    parser.add_argument("--plot-interval", type=int, default=900,
                       help="Interval between plot generation in seconds")
    parser.add_argument("--plot-every-cycle", action="store_true",
                       help="Generate plots after every collection cycle")
    parser.add_argument("--plot-on-completion", action="store_true", default=True,
                       help="Generate plots when nodes complete")
    parser.add_argument("--regenerate-charts", action="store_true",
                       help="Force regeneration of all charts")
    
    # Completion options
    parser.add_argument("--stop-when-all-complete", action="store_true",
                       help="Stop when all discovered nodes are complete")
    
    # Traceroute options  
    parser.add_argument("--no-trace", action="store_true",
                       help="Disable traceroute collection")
    
    args = parser.parse_args()
    
    # Create and run the automated logger
    logger = AutoMeshtasticLogger(args)
    logger.run()


if __name__ == "__main__":
    main()