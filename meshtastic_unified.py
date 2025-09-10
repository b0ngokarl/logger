#!/usr/bin/env python3
"""
Unified Meshtastic Telemetry & Traceroute Logger - Beta Version

This unified script consolidates all functionality into a single interface:
- Data collection (telemetry & traceroute)
- Plotting and dashboard generation
- Node discovery and management
- Real-time monitoring and updates

All features work together seamlessly without needing to run multiple scripts.
This is the beta version that refines existing features and corrects errors.
"""
import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List
import os

# Add core module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from core import (
    discover_all_nodes, collect_nodes_detailed, normalize_node_id,
    collect_telemetry_batch, collect_traceroute_batch,
    setup_telemetry_csv, setup_traceroute_csv,
    iso_now, append_row, LoggerConfig
)


class UnifiedMeshtasticLogger:
    """
    Unified Meshtastic logger that handles all functionality in one interface.
    Combines data collection, plotting, and dashboard generation seamlessly.
    """
    
    def __init__(self, args):
        self.args = args
        self.stop_requested = False
        self.config = LoggerConfig(
            serial_device=args.serial,
            plot_output_dir=str(args.plot_outdir),
            telemetry_csv=args.output,
            traceroute_csv=args.trace_output,
            interval=args.interval,
            timeout=args.timeout
        )
        
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
        
        # Statistics
        self.stats = {
            'cycles_completed': 0,
            'telemetry_points_collected': 0,
            'traceroute_hops_collected': 0,
            'nodes_discovered': 0,
            'last_successful_cycle': None,
            'errors_encountered': 0
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("[INFO] Unified Meshtastic Logger - Beta Version")
        print(f"[INFO] Configuration: {self.config}")
        
        # Initialize system
        self._setup_output_files()
        self._load_node_tracking_data()
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals gracefully."""
        print(f"\\n[INFO] Received signal {signum}, stopping gracefully...", file=sys.stderr)
        self.stop_requested = True
    
    def _setup_output_files(self):
        """Setup output directories and CSV files with proper headers."""
        print("[INFO] Setting up output directories and files...")
        
        # Ensure output directory exists
        self.plot_outdir.mkdir(parents=True, exist_ok=True)
        
        # Setup CSV files
        setup_telemetry_csv(self.tele_csv)
        if not self.args.no_trace:
            setup_traceroute_csv(self.trace_csv)
        
        print(f"[INFO] Output files ready: {self.tele_csv}, {self.trace_csv}")
        print(f"[INFO] Dashboard will be generated at: {self.plot_outdir / 'index.html'}")
    
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
                    self.stats.update(data.get('stats', {}))
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
                    'total_tries': self.total_tries,
                    'stats': self.stats
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
        
        # Update statistics
        self.stats['nodes_discovered'] = len(self.all_nodes)
    
    def _get_target_nodes(self) -> List[str]:
        """Get the list of nodes to collect data from."""
        if self.args.all_nodes:
            discovered = discover_all_nodes(self.args.serial)
            print(f"[INFO] Auto-discovered {len(discovered)} nodes")
            return discovered
        elif self.args.nodes:
            return [normalize_node_id(node) for node in self.args.nodes]
        elif self.args.discover:
            # Discovery mode - show available nodes and exit
            nodes = collect_nodes_detailed(self.args.serial)
            self._display_discovered_nodes(nodes)
            return []
        else:
            return []
    
    def _display_discovered_nodes(self, nodes: List[dict]):
        """Display discovered nodes in a formatted table."""
        if not nodes:
            print("[INFO] No nodes discovered")
            return
        
        print(f"\\n[INFO] Discovered {len(nodes)} nodes:")
        print("-" * 80)
        print(f"{'Node ID':<12} {'User':<20} {'Battery':<8} {'Voltage':<8} {'Last Heard'}")
        print("-" * 80)
        
        for node in sorted(nodes, key=lambda x: x.get('id', '')):
            node_id = node.get('id', 'Unknown')
            user = node.get('user', 'Unknown')[:19]
            battery = f"{node.get('battery_pct', 'N/A')}%"
            voltage = f"{node.get('voltage_v', 'N/A')}V"
            last_heard = node.get('last_heard', 'Unknown')
            
            print(f"{node_id:<12} {user:<20} {battery:<8} {voltage:<8} {last_heard}")
        
        print("-" * 80)
        print("Use --nodes with specific IDs, or --all-nodes to monitor all")
    
    def _collect_and_log_telemetry(self, target_nodes: List[str], cycle_ts: str) -> Dict[str, dict]:
        """Collect and log telemetry data for target nodes."""
        if not target_nodes:
            return {}
        
        print(f"[INFO] Collecting telemetry from {len(target_nodes)} nodes...")
        
        telemetry_data = collect_telemetry_batch(
            target_nodes, 
            self.args.serial, 
            timeout=self.args.timeout
        )
        
        # Log telemetry to CSV
        points_collected = 0
        for node_id, tele in telemetry_data.items():
            if tele:  # Only log if we got data
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
                points_collected += 1
                
                # Update node data
                if node_id in self.all_nodes:
                    self.all_nodes[node_id].update(tele)
                
                print(f"[INFO] Telemetry collected for {node_id}")
        
        self.stats['telemetry_points_collected'] += points_collected
        return telemetry_data
    
    def _collect_and_log_traceroute(self, target_nodes: List[str], cycle_ts: str) -> Dict[str, dict]:
        """Collect and log traceroute data for target nodes."""
        if self.args.no_trace or not target_nodes:
            return {}
        
        print(f"[INFO] Running traceroutes to {len(target_nodes)} nodes...")
        
        traceroute_data = collect_traceroute_batch(
            target_nodes,
            self.args.serial,
            timeout=self.args.timeout
        )
        
        # Log traceroute to CSV
        hops_collected = 0
        for node_id, routes in traceroute_data.items():
            if routes:  # Only log if we got data
                # Log forward hops
                for i, (src, dst, db) in enumerate(routes.get("forward", [])):
                    append_row(self.trace_csv, [cycle_ts, node_id, "forward", i, src, dst, db])
                    hops_collected += 1
                
                # Log backward hops  
                for i, (src, dst, db) in enumerate(routes.get("back", [])):
                    append_row(self.trace_csv, [cycle_ts, node_id, "backward", i, src, dst, db])
                    hops_collected += 1
                
                if routes.get("forward") or routes.get("back"):
                    print(f"[INFO] Traceroute completed for {node_id}")
                else:
                    print(f"[WARN] Traceroute failed for {node_id}")
        
        self.stats['traceroute_hops_collected'] += hops_collected
        return traceroute_data
    
    def _run_integrated_plotting(self):
        """Run integrated plotting with proper Python interpreter detection."""
        if not self.args.plot and not self.args.auto_plot:
            return
        
        try:
            # Use the same Python interpreter that's running this script
            python_executable = sys.executable
            
            plot_cmd = [
                python_executable, "plot_meshtastic.py",
                "--telemetry", str(self.tele_csv),
                "--traceroute", str(self.trace_csv),
                "--outdir", str(self.plot_outdir)
            ]
            
            if self.args.regenerate_charts:
                plot_cmd.append("--regenerate-charts")
                
            if self.args.preserve_history:
                plot_cmd.append("--preserve-history")
            
            print("[INFO] Generating plots and dashboards...")
            subprocess.run(plot_cmd, check=True, capture_output=True, text=True)
            print("[INFO] Plotting completed successfully")
            
            # Show where to find the dashboard
            dashboard_path = self.plot_outdir / "index.html"
            if dashboard_path.exists():
                print(f"[INFO] ✅ Dashboard ready: {dashboard_path.resolve()}")
                print(f"[INFO] Open in browser: file://{dashboard_path.resolve()}")
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Plotting failed: {e}", file=sys.stderr)
            if e.stderr:
                print(f"[ERROR] Details: {e.stderr}", file=sys.stderr)
            self.stats['errors_encountered'] += 1
        except Exception as e:
            print(f"[ERROR] Unexpected plotting error: {e}", file=sys.stderr)
            self.stats['errors_encountered'] += 1
    
    def _run_cycle(self):
        """Run a single data collection cycle."""
        cycle_ts = iso_now()
        self.total_tries += 1
        
        print(f"\\n[INFO] === Cycle {self.total_tries} at {cycle_ts} ===")
        
        try:
            # Discover all nodes for tracking
            all_discovered_nodes = collect_nodes_detailed(self.args.serial)
            self._update_node_tracking(all_discovered_nodes)
            
            # Get target nodes for data collection
            target_nodes = self._get_target_nodes()
            if not target_nodes:
                if not self.args.discover:
                    print("[WARN] No target nodes found for data collection")
                return
            
            print(f"[INFO] Target nodes: {target_nodes}")
            
            # Collect telemetry data
            telemetry_data = self._collect_and_log_telemetry(target_nodes, cycle_ts)
            
            # Collect traceroute data
            traceroute_data = self._collect_and_log_traceroute(target_nodes, cycle_ts)
            
            # Save node tracking data
            self._save_node_tracking_data()
            
            # Run plotting if requested or enabled
            self._run_integrated_plotting()
            
            # Update statistics
            self.stats['cycles_completed'] += 1
            self.stats['last_successful_cycle'] = cycle_ts
            
            print("[INFO] ✅ Cycle completed successfully")
            print(f"[INFO] Telemetry: {len([d for d in telemetry_data.values() if d])} nodes, "
                  f"Traceroute: {len([d for d in traceroute_data.values() if d])} nodes")
            
        except Exception as e:
            print(f"[ERROR] Cycle failed: {e}", file=sys.stderr)
            self.stats['errors_encountered'] += 1
            if self.args.once:
                raise
    
    def _print_final_stats(self):
        """Print final statistics summary."""
        print("\\n" + "="*60)
        print("📊 FINAL STATISTICS")
        print("="*60)
        print(f"Cycles completed: {self.stats['cycles_completed']}")
        print(f"Nodes discovered: {self.stats['nodes_discovered']}")
        print(f"Telemetry points: {self.stats['telemetry_points_collected']}")
        print(f"Traceroute hops: {self.stats['traceroute_hops_collected']}")
        print(f"Errors encountered: {self.stats['errors_encountered']}")
        if self.stats['last_successful_cycle']:
            print(f"Last successful cycle: {self.stats['last_successful_cycle']}")
        
        # Show output files
        print("\\n📁 OUTPUT FILES:")
        if self.tele_csv.exists():
            print(f"Telemetry: {self.tele_csv} ({self.tele_csv.stat().st_size} bytes)")
        if self.trace_csv.exists():
            print(f"Traceroute: {self.trace_csv} ({self.trace_csv.stat().st_size} bytes)")
        
        dashboard_path = self.plot_outdir / "index.html"
        if dashboard_path.exists():
            print(f"\\n🌐 DASHBOARD: file://{dashboard_path.resolve()}")
        
        print("="*60)
    
    def run(self):
        """Main execution loop with comprehensive error handling."""
        print("[INFO] 🚀 Starting Unified Meshtastic Logger")
        print(f"[INFO] Output: telemetry={self.tele_csv}, traceroute={self.trace_csv}")
        print(f"[INFO] Dashboard: {self.plot_outdir}")
        
        # Handle discovery-only mode
        if self.args.discover:
            nodes = collect_nodes_detailed(self.args.serial)
            self._display_discovered_nodes(nodes)
            return
        
        # Main execution loop
        while not self.stop_requested:
            try:
                self._run_cycle()
                
                if self.args.once:
                    break
                
                # Sleep until next cycle
                if not self.stop_requested:
                    print(f"[INFO] 💤 Sleeping for {self.args.interval} seconds...")
                    for _ in range(int(self.args.interval * 10)):
                        if self.stop_requested:
                            break
                        time.sleep(0.1)
                    
            except KeyboardInterrupt:
                print("\\n[INFO] 🛑 Interrupted by user", file=sys.stderr)
                break
            except Exception as e:
                print(f"[ERROR] ❌ Unexpected error in cycle: {e}", file=sys.stderr)
                self.stats['errors_encountered'] += 1
                if self.args.once:
                    break
                # Continue running in interval mode
                print("[INFO] Continuing after error...")
                
        print("\\n[INFO] 🏁 Unified Meshtastic Logger stopped")
        self._print_final_stats()


def parse_args():
    """Parse command-line arguments with comprehensive options."""
    parser = argparse.ArgumentParser(
        description="Unified Meshtastic Telemetry & Traceroute Logger - Beta Version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover available nodes
  %(prog)s --discover
  
  # Monitor specific nodes once with dashboard
  %(prog)s --nodes !abc123 !def456 --once --plot
  
  # Monitor all nodes continuously with auto-plotting
  %(prog)s --all-nodes --auto-plot --interval 300
  
  # Collect data without plotting
  %(prog)s --nodes !abc123 --once --no-plot
  
  # Force regenerate all charts
  %(prog)s --all-nodes --once --plot --regenerate-charts
        """
    )
    
    # Node selection modes
    node_group = parser.add_mutually_exclusive_group()
    node_group.add_argument("--nodes", nargs="+", 
                           help="List of node IDs to monitor (e.g., !abc123 !def456)")
    node_group.add_argument("--all-nodes", action="store_true", 
                           help="Auto-discover and monitor all nodes")
    node_group.add_argument("--discover", action="store_true",
                           help="Discover and display available nodes, then exit")
    
    # Connection options
    parser.add_argument("--serial", 
                       help="Serial device path (e.g., /dev/ttyACM0, auto-detected if not specified)")
    parser.add_argument("--timeout", type=int, default=30,
                       help="Timeout for Meshtastic operations in seconds (default: 30)")
    
    # Output options
    parser.add_argument("--output", default="telemetry.csv", 
                       help="Telemetry CSV output file (default: telemetry.csv)")
    parser.add_argument("--trace-output", default="traceroute.csv", 
                       help="Traceroute CSV output file (default: traceroute.csv)")
    parser.add_argument("--plot-outdir", default="plots", 
                       help="Output directory for plots and HTML dashboard (default: plots)")
    
    # Execution modes
    execution_group = parser.add_mutually_exclusive_group()
    execution_group.add_argument("--once", action="store_true", 
                                help="Run one collection cycle and exit")
    execution_group.add_argument("--interval", type=float, default=300, 
                                help="Interval between cycles in seconds (default: 300)")
    
    # Feature controls
    parser.add_argument("--no-trace", action="store_true", 
                       help="Disable traceroute collection (faster, telemetry only)")
    
    # Plotting options
    plot_group = parser.add_mutually_exclusive_group()
    plot_group.add_argument("--plot", action="store_true", 
                           help="Generate plots and dashboard after data collection")
    plot_group.add_argument("--auto-plot", action="store_true", 
                           help="Automatically generate plots after each cycle")
    plot_group.add_argument("--no-plot", action="store_true", 
                           help="Disable all plotting (data collection only)")
    
    parser.add_argument("--regenerate-charts", action="store_true", 
                       help="Force regeneration of all charts (slower but ensures fresh plots)")
    parser.add_argument("--preserve-history", action="store_true", 
                       help="Create timestamped directories and preserve plot history")
    
    # Advanced options
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output for debugging")
    
    args = parser.parse_args()
    
    # Validation and defaults
    if not any([args.nodes, args.all_nodes, args.discover]):
        parser.error("Must specify one of: --nodes, --all-nodes, or --discover")
    
    # Set auto-plotting as default if plotting is enabled
    if args.plot and not args.no_plot:
        args.auto_plot = True
    
    return args


def main():
    """Main entry point with comprehensive error handling."""
    try:
        args = parse_args()
        
        # Enable verbose logging if requested
        if args.verbose:
            print(f"[DEBUG] Arguments: {args}")
        
        logger = UnifiedMeshtasticLogger(args)
        logger.run()
        return 0
        
    except KeyboardInterrupt:
        print("\\n[INFO] Interrupted by user")
        return 130
    except Exception as e:
        print(f"[ERROR] Failed to start unified logger: {e}", file=sys.stderr)
        if args.verbose if 'args' in locals() else False:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
