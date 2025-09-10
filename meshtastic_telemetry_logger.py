#!/usr/bin/env python3
"""
Meshtastic telemetry & traceroute logger
- Collects telemetry (battery, voltage, channel util, air tx, uptime) and traceroute data from specified nodes
- Appends to CSV files with timestamps
- Optionally auto-plots after each run using plot_meshtastic.py
- Supports single run (--once) or continuous (--interval)
- Interruptible with SIGINT/SIGTERM
"""
import argparse
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import signal
import sys
import time
import subprocess
import re
import json
import pandas as pd

# ---- Telemetry CLI parsing ----
RE_BATT = re.compile(r"Battery level:\s*([0-9.]+)%")
RE_VOLT = re.compile(r"Voltage:\s*([0-9.]+)\s*V")
RE_CHAN = re.compile(r"Total channel utilization:\s*([0-9.]+)%")
RE_AIR  = re.compile(r"Transmit air utilization:\s*([0-9.]+)%")
RE_UP   = re.compile(r"Uptime:\s*([0-9]+)\s*s")

# Import from core modules to avoid duplication
from core import run_cli, iso_now, ensure_header, append_row, discover_all_nodes

# --- Regex patterns for parsing ---

# Match traceroute hop lines: " 1  router1  10.0.0.1  0.123 ms"
RE_HOP = re.compile(r"^\s*\d+\s+(\S+)\s+(\S+)\s+([\d.]+)\s+ms")
# Match forward traceroute section header: "traceroute to ..."
RE_FWD_HDR = re.compile(r"^traceroute to ")
# Match backward traceroute section header: "traceroute from ..."
RE_BWD_HDR = re.compile(r"^traceroute from ")

# --- Meshtastic telemetry and traceroute functions ---

def collect_telemetry_cli(dest: str, serial_dev: Optional[str]=None, timeout: int=30) -> Optional[Dict[str, float]]:
    """Collect telemetry data from a Meshtastic node using the CLI."""
    # Import the proper telemetry collection function from core module
    from core.telemetry import collect_telemetry_cli as core_collect_telemetry
    
    # Use the proper implementation from core module
    return core_collect_telemetry(dest, serial_dev, timeout)

def collect_traceroute_cli(dest: str, serial_dev: Optional[str] = None, timeout: int = 30, retries: int = 3) -> Optional[Dict[str, List[Tuple[str, str, float]]]]:
    """Collect traceroute data from a Meshtastic node using the CLI with retries."""
    if not re.match(r"^![0-9a-zA-Z]+$", dest):
        print(f"[ERROR] Invalid node ID: {dest}", file=sys.stderr)
        return None
    if serial_dev and not re.match(r"^/dev/tty[A-Z]+[0-9]+$", serial_dev):
        print(f"[ERROR] Invalid serial device: {serial_dev}", file=sys.stderr)
        return None

    cmd = ["meshtastic", "--traceroute", dest]
    if serial_dev:
        cmd += ["--port", serial_dev]

    for attempt in range(1, retries + 1):
        ok, out = run_cli(cmd, timeout=timeout)
        if ok:
            # Parse traceroute output
            lines = out.splitlines()
            fwd: List[Tuple[str, str, float]] = []
            bwd: List[Tuple[str, str, float]] = []
            section = None  # "fwd" | "bwd" | None

            # New regex pattern for the actual output format
            route_pattern = re.compile(r'!([0-9a-zA-Z]+)\s+-->\s+!([0-9a-zA-Z]+)\s+\((\d+\.\d+)dB\)')
            
            for line in lines:
                if "Route traced towards destination:" in line:
                    section = "fwd"
                    continue
                if "Route traced back to us:" in line:
                    section = "bwd"
                    continue
                    
                # Try the new format first
                m = route_pattern.search(line)
                if m:
                    a, b, val = f"!{m.group(1)}", f"!{m.group(2)}", float(m.group(3))
                    if section == "bwd":
                        bwd.append((a, b, val))
                    else:
                        fwd.append((a, b, val))
                    continue
                
                # Try the old format as fallback
                m = RE_HOP.search(line)
                if m:
                    a, b, val = m.group(1), m.group(2), float(m.group(3))
                    if section == "bwd":
                        bwd.append((a, b, val))
                    else:
                        fwd.append((a, b, val))

            if fwd or bwd:
                return {"forward": fwd, "back": bwd}
            else:
                print(f"[WARN] No hops parsed for traceroute {dest}. Raw:\n{out}", file=sys.stderr)
        else:
            print(f"[WARN] Traceroute CLI failed for {dest} (Attempt {attempt}/{retries}):\n{out}", file=sys.stderr)

    print(f"[ERROR] Traceroute failed for {dest} after {retries} attempts.", file=sys.stderr)
    return None

# Add a function to run the --nodes command and parse its output
def collect_nodes(timeout: int = 30) -> Optional[List[dict]]:
    """Collect detailed node information using the core module."""
    from core.node_discovery import collect_nodes_detailed
    return collect_nodes_detailed(timeout=timeout)

# Function to update index.html with node information only (no traceroutes)
def update_index_html_with_nodes_only(nodes: List[dict], output_dir: Path):
    index_path = output_dir / "index.html"
    rows = []
    for node in sorted(nodes, key=lambda x: x.get("last_seen", ""), reverse=True):
        lat, lon = node.get("latitude"), node.get("longitude")
        location_link = f"<a href='https://www.openstreetmap.org/?mlat={lat}&mlon={lon}' target='_blank'>{lat}, {lon}</a>" if lat and lon else "N/A"
        rows.append(f"""
        <tr>
            <td>{node['user']}</td>
            <td>{node['id']}</td>
            <td>{node['aka']}</td>
            <td>{location_link}</td>
            <td>{node['last_seen']}</td>
            <td>{node['hops']}</td>
        </tr>
        """)

    table = """
    <table border="1">
        <thead>
            <tr>
                <th>User</th>
                <th>ID</th>
                <th>AKA</th>
                <th>Location</th>
                <th>Last Seen</th>
                <th>Hops</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """.format(rows="\n".join(rows))

    with index_path.open("w", encoding="utf-8") as f:
        f.write(f"<html><body>{table}</body></html>")

# Function to update index.html with node and traceroute information
def update_index_html(nodes: List[dict], output_dir: Path, traceroutes: Dict[str, Dict[str, List[Tuple[str, str, float]]]]):
    index_path = output_dir / "index.html"
    rows = []
    for node in sorted(nodes, key=lambda x: x.get("last_seen", ""), reverse=True):
        lat, lon = node.get("latitude"), node.get("longitude")
        location_link = f"<a href='https://www.openstreetmap.org/?mlat={lat}&mlon={lon}' target='_blank'>{lat}, {lon}</a>" if lat and lon else "N/A"
        traceroute_data = traceroutes.get(node['id'], {})

        # Format traceroute data
        fwd_hops = traceroute_data.get("forward", [])
        bwd_hops = traceroute_data.get("back", [])
        fwd_hops_html = "<ul>" + "".join([f"<li>{a} → {b} ({val} dB)</li>" for a, b, val in fwd_hops]) + "</ul>" if fwd_hops else "N/A"
        bwd_hops_html = "<ul>" + "".join([f"<li>{a} → {b} ({val} dB)</li>" for a, b, val in bwd_hops]) + "</ul>" if bwd_hops else "N/A"

        rows.append(f"""
        <tr>
            <td>{node['user']}</td>
            <td>{node['id']}</td>
            <td>{node['aka']}</td>
            <td>{location_link}</td>
            <td>{node['last_seen']}</td>
            <td>{node['hops']}</td>
            <td>
                <strong>Forward Hops:</strong>
                {fwd_hops_html}
                <strong>Backward Hops:</strong>
                {bwd_hops_html}
            </td>
        </tr>
        """)

    table = """
    <table border="1">
        <thead>
            <tr>
                <th>User</th>
                <th>ID</th>
                <th>AKA</th>
                <th>Location</th>
                <th>Last Seen</th>
                <th>Hops</th>
                <th>Traceroutes</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    <script>
        function filterHops() {{
            const rows = document.querySelectorAll('tbody tr');
            rows.forEach(row => {{
                const hops = row.cells[5].innerText;
                row.style.display = hops === 'N/A' ? 'none' : '';
            }});
        }}
    </script>
    <button onclick="filterHops()">Show Only Nodes with Hops</button>
    """.format(rows="\n".join(rows))

    with index_path.open("w", encoding="utf-8") as f:
        f.write(f"<html><body>{table}</body></html>")

# ---- Main ----

def parse_args():
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

_stop = False
def _sig_handler(signum, frame):
    global _stop
    _stop = True
    print("\n[INFO] Stopping...", file=sys.stderr)

def main():
    args = parse_args()
    tele_csv = Path(args.output)
    trace_csv = Path(args.trace_output)
    plot_outdir = Path(args.plot_outdir)
    diagnostics_path = plot_outdir / "diagnostics.html"
    
    # Handle automatic node discovery if requested
    if args.all_nodes:
        try:
            # Discover all nodes
            print("[INFO] Discovering all nodes on the network...")
            discovered_nodes = discover_all_nodes(args.serial)
            if discovered_nodes:
                print(f"[INFO] Discovered {len(discovered_nodes)} nodes: {', '.join(discovered_nodes)}")
                args.nodes = discovered_nodes
            else:
                print("[ERROR] No nodes discovered. Exiting.", file=sys.stderr)
                return 1
        except Exception as e:
            print(f"[ERROR] Failed to discover nodes: {e}", file=sys.stderr)
            return 1
    
    # Node tracking data structures
    node_seen_counts = {}  # {node_id: seen_count}
    all_nodes = {}  # {node_id: node_data} - Persistent store of all nodes ever discovered
    node_first_seen = {}  # {node_id: timestamp} - When node was first discovered
    node_last_seen = {}   # {node_id: timestamp} - When node was last seen
    total_tries = 0

    ensure_header(tele_csv, ["timestamp","node","battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s"])
    ensure_header(trace_csv, ["timestamp","dest","direction","hop_index","from","to","link_db"])

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    # Create plots directory if it doesn't exist
    plot_outdir.mkdir(exist_ok=True, parents=True)

    # Load existing node data if available
    nodes_json_path = plot_outdir / "nodes.json"
    if nodes_json_path.exists():
        try:
            with open(nodes_json_path, 'r') as f:
                saved_data = json.load(f)
                all_nodes = saved_data.get('all_nodes', {})
                node_seen_counts = saved_data.get('node_seen_counts', {})
                node_first_seen = saved_data.get('node_first_seen', {})
                node_last_seen = saved_data.get('node_last_seen', {})
                total_tries = saved_data.get('total_tries', 0)
                print(f"[INFO] Loaded data for {len(all_nodes)} previously discovered nodes")
        except Exception as e:
            print(f"[WARN] Could not load saved node data: {e}", file=sys.stderr)

    # Collect all nodes initially
    nodes = collect_nodes() or []
    # We'll generate HTML files in a single batch at the end
    
    # Only run telemetry and traceroute for nodes specified in --nodes
    while True:
        cycle_ts = iso_now()
        total_tries += 1
        print(f"[INFO] Starting collection cycle {total_tries} at {cycle_ts}")
        
        # Run meshtastic --nodes before each cycle
        nodes = collect_nodes() or []
        
        # Update the node tracking data
        current_ts = iso_now()
        for node in nodes:
            node_id = node.get("id")
            if node_id:
                # Update seen count
                node_seen_counts[node_id] = node_seen_counts.get(node_id, 0) + 1
                
                # Update first/last seen timestamps
                if node_id not in node_first_seen:
                    node_first_seen[node_id] = current_ts
                node_last_seen[node_id] = current_ts
                
                # Store the updated node data
                all_nodes[node_id] = node
        
        # Save node data to json
        try:
            with open(nodes_json_path, 'w') as f:
                json.dump({
                    'all_nodes': all_nodes,
                    'node_seen_counts': node_seen_counts,
                    'node_first_seen': node_first_seen,
                    'node_last_seen': node_last_seen,
                    'total_tries': total_tries
                }, f)
        except Exception as e:
            print(f"[WARN] Could not save node data: {e}", file=sys.stderr)
        
        # Create a list of all nodes, including those seen in previous runs
        all_nodes_list = list(all_nodes.values())
        
        # Sort all nodes by last seen timestamp (most recent first)
        sorted_nodes = sorted(
            all_nodes_list, 
            key=lambda x: node_last_seen.get(x.get("id", ""), ""), 
            reverse=True
        )

        # Collect telemetry and traceroute data ONLY for nodes specified in --nodes
        telemetry_data = {}
        traceroutes = {}
        for node_id in args.nodes:
            # Normalize node ID by ensuring it has ! prefix for CLI commands
            normalized_node_id = node_id.strip('!')
            cli_node_id = f"!{normalized_node_id}" if normalized_node_id else node_id
            
            # Collect telemetry
            print(f"[INFO] Collecting telemetry for specified node: {cli_node_id}")
            tele = collect_telemetry_cli(cli_node_id, serial_dev=args.serial)
            print(f"[DEBUG] Telemetry collection result for {cli_node_id}: {tele}")
            if tele:
                telemetry_data[cli_node_id] = tele
                # Log telemetry data to CSV
                append_row(tele_csv, [
                    cycle_ts, cli_node_id, 
                    tele.get("battery_pct", ""),
                    tele.get("voltage_v", ""),
                    tele.get("channel_util_pct", ""),
                    tele.get("air_tx_pct", ""),
                    tele.get("uptime_s", "")
                ])
                print(f"[INFO] Telemetry logged for {cli_node_id}")
                
                # Update the node data in the all_nodes dictionary
                print(f"[DEBUG] Updating node {node_id} with telemetry data in all_nodes")
                if node_id in all_nodes:
                    for key, value in tele.items():
                        all_nodes[node_id][key] = value
                    print(f"[DEBUG] Updated node data: {all_nodes[node_id]}")
                else:
                    print(f"[DEBUG] Node {node_id} not found in all_nodes")
            
            # Collect traceroute if not disabled
            if not args.no_trace:
                print(f"[INFO] Running traceroute for specified node: {cli_node_id}")
                tr = collect_traceroute_cli(dest=cli_node_id, serial_dev=args.serial)
                if tr:
                    traceroutes[cli_node_id] = tr
                    # Log forward hops
                    for i, (src, dst, db) in enumerate(tr.get("forward", [])):
                        append_row(trace_csv, [cycle_ts, cli_node_id, "forward", i, src, dst, db])
                    # Log backward hops
                    for i, (src, dst, db) in enumerate(tr.get("back", [])):
                        append_row(trace_csv, [cycle_ts, cli_node_id, "backward", i, src, dst, db])
                    print(f"[INFO] Traceroute logged for {cli_node_id}")

        # Prepare to generate all HTML files in one pass
        print("[INFO] Generating HTML dashboards and diagnostics...")
        
        # Export diagnostics.html with improved traceroute presentation
        rows = []
        for node in sorted_nodes:
            node_id = node.get("id")
            if not node_id:
                continue
                
            # Get node statistics
            seen = node_seen_counts.get(node_id, 0)
            first_seen_date = node_first_seen.get(node_id, "Unknown")
            last_seen_date = node_last_seen.get(node_id, "Unknown")
            uptime_s = node.get("uptime_s", "N/A")
            uptime_hours = float(uptime_s) / 3600 if uptime_s and uptime_s != "N/A" else "N/A"
            
            # Calculate seen percentage
            percent = f"{(seen/total_tries*100):.1f}%" if total_tries > 0 else "0%"
            seen_stats = f"{seen} of {total_tries} cycles ({percent})"
            
            # Get location info
            lat, lon = node.get("latitude"), node.get("longitude")
            location_link = f"<a href='https://www.openstreetmap.org/?mlat={lat}&mlon={lon}' target='_blank'>{lat}, {lon}</a>" if lat and lon else "N/A"
            
            # Add telemetry data if available
            telemetry_html = "N/A"
            if node.get("battery_pct") is not None or node.get("voltage_v") is not None:
                battery = node.get("battery_pct", "N/A")
                voltage = node.get("voltage_v", "N/A")
                channel_util = node.get("channel_util_pct", "N/A")
                air_tx = node.get("air_tx_pct", "N/A")
                
                telemetry_html = f"""
                <div class="telemetry-pills">
                    <span class="pill">🔋 {battery}%</span>
                    <span class="pill">⚡ {voltage}V</span>
                    <span class="pill">📡 {channel_util}%</span>
                    <span class="pill">📻 {air_tx}%</span>
                    <span class="pill">⏱️ {uptime_hours if uptime_hours != "N/A" else "N/A"} hrs</span>
                </div>
                """
            
            # Traceroute presentation
            tr = traceroutes.get(node_id)
            if tr:
                fwd = tr.get("forward", [])
                bwd = tr.get("back", [])
                # Create a better visualization for the traceroute data
                fwd_html = ""
                if fwd:
                    fwd_html = "<div class='trace-path'>"
                    for i, (a, b, val) in enumerate(fwd):
                        fwd_html += f"""
                        <div class='hop'>
                            <div class='hop-num'>{i+1}</div>
                            <div class='hop-from'>{a}</div>
                            <div class='hop-arrow'>→</div>
                            <div class='hop-to'>{b}</div>
                            <div class='hop-db'>{val} dB</div>
                        </div>
                        """
                    fwd_html += "</div>"
                else:
                    fwd_html = "<em>No forward hops</em>"
                    
                bwd_html = ""
                if bwd:
                    bwd_html = "<div class='trace-path'>"
                    for i, (a, b, val) in enumerate(bwd):
                        bwd_html += f"""
                        <div class='hop'>
                            <div class='hop-num'>{i+1}</div>
                            <div class='hop-from'>{a}</div>
                            <div class='hop-arrow'>→</div>
                            <div class='hop-to'>{b}</div>
                            <div class='hop-db'>{val} dB</div>
                        </div>
                        """
                    bwd_html += "</div>"
                else:
                    bwd_html = "<em>No backward hops</em>"
                    
                traceroute_html = f"""
                <div class='traceroute'>
                    <div class='trace-section'>
                        <h4>Forward Path</h4>
                        {fwd_html}
                    </div>
                    <div class='trace-section'>
                        <h4>Backward Path</h4>
                        {bwd_html}
                    </div>
                </div>
                <style>
                    .traceroute {{
                        margin: 10px 0;
                    }}
                    .trace-section {{
                        margin-bottom: 15px;
                    }}
                    .trace-path {{
                        border: 1px solid #ddd;
                        padding: 10px;
                        border-radius: 4px;
                    }}
                    .hop {{
                        display: flex;
                        align-items: center;
                        margin-bottom: 5px;
                        padding: 5px;
                        background-color: #f9f9f9;
                    }}
                    .hop-num {{
                        background-color: #4CAF50;
                        color: white;
                        border-radius: 50%;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-right: 10px;
                    }}
                    .hop-arrow {{
                        margin: 0 8px;
                        color: #666;
                    }}
                    .hop-db {{
                        margin-left: auto;
                        font-weight: bold;
                        background-color: #f0f0f0;
                        padding: 2px 6px;
                        border-radius: 3px;
                    }}
                </style>
                """
            else:
                traceroute_html = "<em>No traceroute data</em>"
                
            rows.append(f"""
            <tr>
                <td>{node.get('user', 'Unknown')}</td>
                <td>{node_id}</td>
                <td>{node.get('aka', '')}</td>
                <td>{location_link}</td>
                <td>
                    <div>First: {first_seen_date}</div>
                    <div>Last: {last_seen_date}</div>
                </td>
                <td>{node.get('hops', 'N/A')}</td>
                <td>{seen_stats}</td>
                <td>{telemetry_html}</td>
                <td>{traceroute_html}</td>
            </tr>
            """)
        
        # Add CSS for telemetry pills
        table_css = """
        <style>
            table {border-collapse: collapse; width: 100%; margin-top: 20px;}
            th, td {text-align: left; padding: 8px; border: 1px solid #ddd;}
            tr:nth-child(even) {background-color: #f2f2f2;}
            th {background-color: #4CAF50; color: white;}
            .telemetry-pills {display: flex; flex-wrap: wrap; gap: 5px;}
            .pill {
                background-color: #f1f1f1;
                padding: 4px 8px;
                border-radius: 16px;
                font-size: 12px;
                display: inline-block;
                margin-bottom: 3px;
            }
        </style>
        """
        
        table = f"""
        <h1>Meshtastic Network Diagnostics</h1>
        <p>Last updated: {iso_now()} - Total cycles: {total_tries}</p>
        {table_css}
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th>ID</th>
                    <th>AKA</th>
                    <th>Location</th>
                    <th>Seen Timestamps</th>
                    <th>Hops</th>
                    <th>Connectivity</th>
                    <th>Telemetry</th>
                    <th>Traceroute</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
        
        # Create a complete HTML page with better formatting
        html_page = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meshtastic Network Diagnostics</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c7a2c;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .nav-links {{
            margin: 20px 0;
        }}
        .nav-links a {{
            display: inline-block;
            margin-right: 15px;
            color: #0066cc;
            text-decoration: none;
        }}
        .nav-links a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav-links">
            <a href="index.html">Home</a>
            <a href="dashboards.html">Node Dashboards</a>
            <a href="nodes.html">All Nodes</a>
        </div>
        
        {table}
        
        <div class="nav-links" style="margin-top: 30px;">
            <a href="index.html">Back to Home</a>
        </div>
    </div>
</body>
</html>"""
        
        # 1. First write the diagnostics.html file
        with diagnostics_path.open("w", encoding="utf-8") as f:
            f.write(html_page)
        print("[INFO] Generated diagnostics.html with detailed node information")
        
        # 2. Now prepare the index.html with traceroute information
        # This is simplified from the original update_index_html function
        # We skip this call since we'll generate a custom index later
        
        # Next, update individual node pages with both telemetry and traceroute data
        try:
            # Debug: Print the nodes data to see what we're working with
            print(f"[DEBUG] Nodes data available: {len(sorted_nodes)} nodes")
            if sorted_nodes:
                print(f"[DEBUG] Sample node data: {sorted_nodes[0]}")
            
            # Import the update_node_pages module dynamically
            update_node_pages_path = Path(__file__).parent / "update_node_pages.py"
            if update_node_pages_path.exists():
                spec = importlib.util.spec_from_file_location("update_node_pages", update_node_pages_path)
                if spec and spec.loader:
                    update_node_pages_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(update_node_pages_module)
                    
                    # Count how many pages we update
                    pages_updated = 0
                    print("[DEBUG] Starting node page updates...")
                    
                    # For each node with telemetry data, create/update its page
                    for node in sorted_nodes:
                        node_id = node.get("id", "")
                        if node_id:
                            # Get latest telemetry for this node from the collected data
                            telemetry_data = {}
                            for metric in ["battery_pct", "voltage_v", "channel_util_pct", "air_tx_pct", "uptime_s"]:
                                if metric in node:
                                    telemetry_data[metric] = node[metric]
                            
                            print(f"[DEBUG] Node {node_id} metrics from node object: {[m for m in ['battery_pct', 'voltage_v', 'channel_util_pct', 'air_tx_pct', 'uptime_s'] if m in node]}")
                            print(f"[DEBUG] Node {node_id} telemetry data extracted: {telemetry_data}")
                            
                            # If telemetry data is empty, try to load the latest from telemetry_log.csv
                            if not telemetry_data and Path("telemetry_log.csv").exists():
                                try:
                                    # Normalize node ID by removing ! prefix
                                    normalized_node_id = node_id.strip('!')
                                    print(f"[DEBUG] Looking for historical data for node {normalized_node_id} in telemetry_log.csv")
                                    
                                    # Read the file and find entries for this node based on normalized ID
                                    matching_lines = []
                                    
                                    # Use subprocess to safely grep the file
                                    import subprocess
                                    try:
                                        # Use grep with -F for fixed strings to avoid regex interpretation
                                        result = subprocess.run(
                                            ["grep", normalized_node_id, "telemetry_log.csv"],
                                            capture_output=True,
                                            text=True,
                                            check=False  # Don't raise exception if grep doesn't find matches
                                        )
                                        if result.stdout:
                                            matching_lines = result.stdout.strip().split('\n')
                                    except Exception as grep_err:
                                        print(f"[WARN] Error using grep to find node data: {grep_err}", file=sys.stderr)
                                        # Fall back to manual search if grep fails
                                        with open("telemetry_log.csv", "r") as f:
                                            for line in f:
                                                if normalized_node_id in line:
                                                    matching_lines.append(line.strip())
                                    
                                    # For each metric, find the most recent non-empty value
                                    if matching_lines:
                                        # Initialize metrics we want to find
                                        metrics = ["battery_pct", "voltage_v", "channel_util_pct", "air_tx_pct", "uptime_s"]
                                        
                                        # Start from the most recent entries
                                        for line in reversed(matching_lines):
                                            parts = line.split(",")
                                            if len(parts) >= 7:  # Make sure line has enough fields
                                                # Check each metric position
                                                for i, metric in enumerate(metrics):
                                                    # Only process if we haven't found this metric yet
                                                    if metric not in telemetry_data and parts[i+2].strip():
                                                        try:
                                                            telemetry_data[metric] = float(parts[i+2])
                                                        except ValueError:
                                                            pass  # Ignore invalid values
                                        
                                        print(f"[DEBUG] Loaded historical telemetry data for {normalized_node_id}: {telemetry_data}")
                                except Exception as e:
                                    print(f"[WARN] Error loading historical data for {normalized_node_id}: {e}", file=sys.stderr)
                            
                                # Get node data from all_nodes dictionary (if available)
                            if node_id in all_nodes:
                                node_info = all_nodes.get(node_id, {})
                                # Add node info to telemetry data
                                for key, value in node_info.items():
                                    if key not in telemetry_data:  # Don't overwrite telemetry data with node info
                                        telemetry_data[key] = value
                                print(f"[DEBUG] Enhanced telemetry data with node info from all_nodes for {node_id}")
                                
                            # Get traceroute data for this node if available
                            traceroute_data = traceroutes.get(node_id)
                            
                            # Print debug information about telemetry and traceroute data
                            print(f"[DEBUG] Node {node_id} telemetry data: {telemetry_data}")
                            print(f"[DEBUG] Node {node_id} traceroute data: {traceroute_data}")                            # Update the node's page if we have telemetry OR traceroute data
                            if telemetry_data or traceroute_data:
                                print(f"[DEBUG] Updating page for node {node_id}")
                                update_node_pages_module.update_node_pages(
                                    node_id,
                                    telemetry_data,
                                    traceroute_data,
                                    plot_outdir
                                )
                                pages_updated += 1
                                pages_updated += 1
                    
                    if pages_updated > 0:
                        print(f"[INFO] Updated {pages_updated} node pages with telemetry and traceroute data")
                    else:
                        print("[WARN] No node pages were updated - check if telemetry data is being collected", file=sys.stderr)
                    
                    # Print summary of pages updated
                    if pages_updated > 0:
                        print(f"[INFO] Updated {pages_updated} node pages with telemetry and traceroute data")
                    else:
                        print("[WARN] No node pages were updated initially - traceroute data will be applied after plotting")
                else:
                    print("[WARN] Could not load update_node_pages.py module", file=sys.stderr)
            else:
                print(f"[WARN] Node pages module not found at {update_node_pages_path}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Failed to update node pages: {e}", file=sys.stderr)
        
        # Create a list of nodes with data for the dashboards page
        dashboards_path = plot_outdir / "dashboards.html"
        nodes_with_data = []
        for node in sorted_nodes:
            node_id = node.get("id", "")
            if node_id:
                nodes_with_data.append(node)
        
        # Create dashboards.html with links to individual node pages
        dashboards_html = f"""<!doctype html>
<meta charset='utf-8'>
<title>Node Dashboards</title>
<style>
body {{font-family: Arial, sans-serif; margin: 20px;}}
.dashboard-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-top: 20px;
}}
.node-card {{
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}}
.node-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.15);
}}
.node-id {{
    font-family: monospace;
    background-color: #f5f5f5;
    padding: 3px 6px;
    border-radius: 3px;
    font-size: 14px;
    margin-left: 8px;
}}
.node-metrics {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
    margin-top: 15px;
}}
.metric {{
    background-color: #f9f9f9;
    padding: 8px;
    border-radius: 4px;
    text-align: center;
}}
.metric-name {{
    font-size: 12px;
    color: #666;
}}
.metric-value {{
    font-size: 16px;
    font-weight: bold;
    margin-top: 5px;
}}
.view-btn {{
    display: inline-block;
    background-color: #4CAF50;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    margin-top: 15px;
    text-decoration: none;
    text-align: center;
}}
.view-btn:hover {{
    background-color: #45a049;
}}
h1 {{margin-bottom: 10px;}}
</style>
<h1>Node Dashboards</h1>
<p>Last updated: {iso_now()} - {len(nodes_with_data)} nodes with data</p>
<p><a href="index.html">Back to index</a></p>

<div class="dashboard-grid">
"""
        # Process each node for the dashboard
        for node in nodes_with_data:
            node_id = node.get("id", "")
            if not node_id:
                continue
                
            clean_id = node_id.replace("!", "")
            user = node.get("user", "Unknown")
            aka = node.get("aka", "")
            battery = node.get("battery_pct", "N/A")
            voltage = node.get("voltage_v", "N/A")
            
            # Add node card with key metrics and link to its dedicated page
            dashboards_html += f"""
    <div class="node-card">
        <h3>{user or "Unknown"} <span class="node-id">{node_id}</span></h3>
        {f'<p>{aka}</p>' if aka else ''}
        <div class="node-metrics">
            <div class="metric">
                <div class="metric-name">Battery</div>
                <div class="metric-value">{battery}%</div>
            </div>
            <div class="metric">
                <div class="metric-name">Voltage</div>
                <div class="metric-value">{voltage} V</div>
            </div>
        </div>
        <a href="node_{clean_id}/index.html" class="view-btn">View Details</a>
    </div>"""
        
        dashboards_html += """
</div>
</html>
"""
        # Write the dashboards HTML file
        with dashboards_path.open("w", encoding="utf-8") as f:
            f.write(dashboards_html)
        print(f"[INFO] Generated dashboards.html with {len(nodes_with_data)} node cards")
        
        # Create a new file called nodes.html with all discovered nodes
        nodes_path = plot_outdir / "nodes.html"
        nodes_html = f"""<!doctype html><meta charset='utf-8'><title>All Discovered Nodes</title>
<style>
body {{font-family: Arial, sans-serif; margin: 20px;}}
table {{border-collapse: collapse; width: 100%;}}
th, td {{text-align: left; padding: 8px; border: 1px solid #ddd;}}
tr:nth-child(even) {{background-color: #f2f2f2;}}
th {{background-color: #4CAF50; color: white;}}
</style>
<h1>All Discovered Nodes ({len(nodes_with_data)})</h1>
<p>Last updated: {iso_now()}</p>
<table>
<thead>
    <tr>
        <th>User</th>
        <th>ID</th>
        <th>AKA</th>
        <th>Last Seen</th>
        <th>Location</th>
        <th>Hops</th>
    </tr>
</thead>
<tbody>
{"".join([f"<tr><td>{node.get('user', 'Unknown')}</td><td>{node.get('id', 'Unknown')}</td><td>{node.get('aka', 'Unknown')}</td><td>{node.get('last_seen', 'Unknown')}</td><td>{node.get('latitude', 'N/A')}, {node.get('longitude', 'N/A')}</td><td>{node.get('hops', 'N/A')}</td></tr>" for node in nodes_with_data])}
</tbody>
</table>
<p><a href='index.html'>Back to index</a></p>
"""
        with nodes_path.open("w", encoding="utf-8") as f:
            f.write(nodes_html)
        print(f"[INFO] Generated nodes.html with {len(nodes_with_data)} nodes")
        
        # Create our own custom index.html file with links to everything
        index_path = plot_outdir / "index.html"
        index_html = f"""<!doctype html>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Meshtastic Telemetry & Traceroute</title>
<style>
    body {{font-family: Arial, sans-serif; margin: 20px;}}
    .card-container {{display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px;}}
    .card {{
        border: 1px solid #ddd; border-radius: 8px; padding: 20px;
        width: 300px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    h1, h2 {{color: #333;}}
    a {{text-decoration: none; color: #0066cc;}}
    a:hover {{text-decoration: underline;}}
    .stats {{background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-top: 20px;}}
</style>
<h1>Meshtastic Telemetry & Traceroute</h1>
<p>Last updated: {iso_now()}</p>

<div class="stats">
    <h3>Statistics</h3>
    <ul>
        <li><strong>Total nodes discovered:</strong> {len(nodes_with_data)}</li>
        <li><strong>Nodes with traceroute data:</strong> {len(traceroutes)}</li>
    </ul>
</div>

<h2>Navigation</h2>
<div class="card-container">
    <div class="card">
        <h3>Node Information</h3>
        <ul>
            <li><a href="nodes.html">All Discovered Nodes ({len(nodes_with_data)})</a></li>
            <li><a href="dashboards.html">Node Dashboards</a></li>
            <li><a href="diagnostics.html">Diagnostics</a></li>
        </ul>
    </div>
    <div class="card">
        <h3>Plots</h3>
        <ul>
            <li><a href="traceroute_hops.png">Traceroute Hops</a></li>
            <li><a href="traceroute_bottleneck_db.png">Traceroute Bottleneck</a></li>
        </ul>
    </div>
    <div class="card">
        <h3>Data Files</h3>
        <ul>
            <li>Telemetry: <a href="../{args.output}">{args.output}</a></li>
            <li>Traceroute: <a href="../{args.trace_output}">{args.trace_output}</a></li>
        </ul>
    </div>
</div>

<h2>Topology Snapshots</h2>
<div class="card-container">
{"".join([f'<div class="card"><img src="{topo_file}" alt="{topo_file}" style="max-width:100%;"></div>' for topo_file in [f for f in os.listdir(plot_outdir) if f.startswith('topology_') and f.endswith('.png')][:6]])}
</div>
"""
        with index_path.open("w", encoding="utf-8") as f:
            f.write(index_html)
        print("[INFO] Generated index.html with navigation and statistics")

        # Create pages for all nodes found via meshtastic --nodes
        print("[INFO] Creating pages for all discovered nodes...")
        success, nodes_output = run_cli(["meshtastic", "--nodes"])
        all_discovered_nodes = []
        if success:
            # Parse the nodes output to extract all node IDs
            lines = nodes_output.splitlines()
            for line in lines:
                    if "!" in line and "│" in line:
                        parts = line.split("│")
                        if len(parts) >= 3:  # Node ID is typically in the 3rd column
                            node_id = parts[2].strip()
                            if node_id.startswith("!") and len(node_id) > 1:
                                all_discovered_nodes.append(node_id)
                                
                                # Extract all node information from the line
                                if len(parts) >= 15:  # Ensure we have enough parts to parse
                                    node_info = {
                                        'user': parts[1].strip(),
                                        'id': parts[2].strip(),
                                        'aka': parts[3].strip(),
                                        'hardware': parts[4].strip(),
                                        'key': parts[5].strip(),
                                        'firmware': parts[6].strip(),
                                        'latitude': parts[7].strip(),
                                        'longitude': parts[8].strip(),
                                        'altitude': parts[9].strip(),
                                        'signal_strength': parts[10].strip(),
                                        'channel_util_pct': float(parts[11].strip().rstrip('%')) if parts[11].strip().rstrip('%').replace('.', '', 1).isdigit() else 0.0,
                                        'air_tx_pct': float(parts[12].strip().rstrip('%')) if parts[12].strip().rstrip('%').replace('.', '', 1).isdigit() else 0.0,
                                        'hops': parts[13].strip(),
                                        'last_seen': parts[14].strip()
                                    }
                                    
                                    # Store this information in all_nodes
                                    all_nodes[node_id] = node_info
            
            print(f"[INFO] Found {len(all_discovered_nodes)} nodes from meshtastic --nodes")
            
            # Load the update_node_pages module if not already loaded
            if 'update_node_pages_module' not in locals():
                update_node_pages_path = Path(__file__).parent / "update_node_pages.py"
                if update_node_pages_path.exists():
                    try:
                        spec = importlib.util.spec_from_file_location("update_node_pages", update_node_pages_path)
                        update_node_pages_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(update_node_pages_module)
                    except Exception as e:
                        print(f"[WARN] Could not load update_node_pages.py module: {e}", file=sys.stderr)
                        update_node_pages_module = None
                else:
                    print(f"[WARN] Node pages module not found at {update_node_pages_path}", file=sys.stderr)
                    update_node_pages_module = None
            
            # Create or update pages for all discovered nodes
            if update_node_pages_module:
                pages_created = 0
                for node_id in all_discovered_nodes:
                    # Get the normalized node ID (without ! prefix)
                    normalized_node_id = node_id.strip('!')
                    
                    # Get node data from all_nodes dictionary (if available)
                    node_data = {}
                    
                    # Check if we have the node in our all_nodes dictionary
                    if node_id in all_nodes:
                        node_data = all_nodes.get(node_id, {})
                        print(f"[DEBUG] Found existing node data for {node_id}: {node_data}")
                    
                    # For nodes from nodes table, make sure node_info is included in telemetry data
                    # These values are already in node_data from all_nodes, no need to create a separate dictionary
                    
                    # Also try to load historical telemetry data
                    normalized_node_id = node_id.strip('!')
                    telemetry_file = Path(args.output)
                    
                    # Try to load historical telemetry data
                    if telemetry_file.exists():
                        try:
                            df = pd.read_csv(telemetry_file)
                            # Filter for this node
                            node_data_df = df[df['node_id'] == normalized_node_id]
                            if not node_data_df.empty:
                                # Get the latest row
                                latest_row = node_data_df.iloc[-1]
                                # Add metrics to node_data
                                for col in df.columns:
                                    if col != 'node_id' and col != 'timestamp':
                                        try:
                                            node_data[col] = latest_row[col]
                                        except:
                                            pass
                        except Exception as e:
                            print(f"[WARN] Error loading telemetry for {node_id}: {e}", file=sys.stderr)
                            
                        print(f"[DEBUG] Enhanced node data with telemetry for {node_id}: {node_data}")
                    
                    # Get traceroute data for this node (if available)
                    traceroute_data = traceroutes.get(node_id)
                    
                    # Create/update the node page
                    try:
                        update_node_pages_module.update_node_pages(
                            node_id,
                            node_data,
                            traceroute_data,
                            plot_outdir
                        )
                        pages_created += 1
                    except Exception as e:
                        print(f"[WARN] Failed to create page for node {node_id}: {e}", file=sys.stderr)
                
                print(f"[INFO] Created/updated pages for {pages_created} nodes from all discovered nodes")
        
        # Run auto-plotting if enabled
        if not args.no_plot:
            print("[INFO] Running auto-plotting...")
            try:
                plot_cmd = [
                    "python3", "plot_meshtastic.py",
                    "--telemetry", args.output,
                    "--traceroute", args.trace_output,
                    "--outdir", args.plot_outdir
                ]
                
                # Add regenerate-charts flag if specified
                if args.regenerate_charts:
                    plot_cmd.append("--regenerate-charts")
                subprocess.run(plot_cmd, check=False)
                print(f"[INFO] Plots generated in {args.plot_outdir}/")
                
                # Re-run our update_node_pages for each node with traceroute data to restore traceroute visualizations
                print("[DEBUG] Re-applying traceroute visualizations after plotting...")
                
                # Import the NodePageUpdater class
                node_updater_path = Path(__file__).parent / "node_page_updater.py"
                if node_updater_path.exists():
                    try:
                        spec = importlib.util.spec_from_file_location("node_page_updater", node_updater_path)
                        if spec and spec.loader:
                            node_updater_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(node_updater_module)
                            
                            # Create a NodePageUpdater
                            updater = node_updater_module.NodePageUpdater(args.plot_outdir)
                            
                            # First update nodes with traceroute data
                            if traceroutes:
                                for node_id, tr_data in traceroutes.items():
                                    # We need to reuse existing telemetry data for this node
                                    print(f"[DEBUG] Re-applying traceroute visualization for {node_id}")
                                    
                                    # First try to extract telemetry from the current data
                                    node_telemetry = {}
                                    
                                    # Try to find the node in all_nodes
                                    node_found = False
                                    for node in all_nodes_list:
                                        if node.get("id") == node_id:
                                            node_found = True
                                            # Extract known telemetry metrics
                                            for metric in ["battery_pct", "voltage_v", "channel_util_pct", "air_tx_pct", "uptime_s"]:
                                                if metric in node:
                                                    node_telemetry[metric] = node[metric]
                                        
                                    # If not found in current data or no telemetry, try to load from history
                                    if not node_found or not node_telemetry:
                                        try:
                                            # Use a better matching approach for node IDs
                                            normalized_node_id = node_id.strip('!')
                                            print(f"[DEBUG] Looking for historical data for node {node_id} in telemetry_log.csv")
                                            
                                            # Use subprocess to safely grep the file
                                            try:
                                                # Use grep with -F for fixed strings to avoid regex interpretation
                                                grep_result = subprocess.run(
                                                    ["grep", normalized_node_id, "telemetry_log.csv"],
                                                    capture_output=True,
                                                    text=True,
                                                    check=False  # Don't raise exception if grep doesn't find matches
                                                )
                                                if grep_result.stdout:
                                                    matching_lines = grep_result.stdout.strip().split('\n')
                                                    
                                                    # For each metric, find the most recent non-empty value
                                                    if matching_lines:
                                                        # Initialize metrics we want to find
                                                        metrics = ["battery_pct", "voltage_v", "channel_util_pct", "air_tx_pct", "uptime_s"]
                                                        
                                                        # Start from the most recent entries
                                                        for line in reversed(matching_lines):
                                                            parts = line.split(",")
                                                            if len(parts) >= 7:  # Make sure line has enough fields
                                                                # Check each metric position
                                                                for i, metric in enumerate(metrics):
                                                                    # Only process if we haven't found this metric yet
                                                                    if metric not in node_telemetry and parts[i+2].strip():
                                                                        try:
                                                                            node_telemetry[metric] = float(parts[i+2])
                                                                        except ValueError:
                                                                            pass  # Ignore invalid values
                                                
                                                                # If we found all metrics, we can stop searching
                                                                if all(m in node_telemetry for m in metrics):
                                                                    break
                                            except Exception as e:
                                                print(f"[WARN] Error using grep to find node data: {e}", file=sys.stderr)
                                            
                                            print(f"[DEBUG] Loaded historical telemetry data for {node_id}: {node_telemetry}")
                                        except Exception as e:
                                            print(f"[WARN] Error loading historical data for {node_id}: {e}", file=sys.stderr)
                                
                                update_node_pages_module.update_node_pages(
                                    node_id,
                                    node_telemetry,  # Use the loaded telemetry data
                                    tr_data,
                                    plot_outdir
                                )
                    except Exception as e:
                        print(f"[WARN] Failed to re-apply traceroute visualizations: {e}", file=sys.stderr)
                
                # Final step: Update the dashboard.html file with our grid layout
                print("[INFO] Updating dashboard layout...")
                dashboard_updater = Path(__file__).parent / "update_dashboard.py"
                if dashboard_updater.exists():
                    try:
                        subprocess.run(["python3", str(dashboard_updater)], check=False)
                        print("[INFO] Dashboard layout updated successfully")
                    except Exception as e:
                        print(f"[WARN] Dashboard update failed: {e}", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] Auto-plotting failed: {e}", file=sys.stderr)

        if args.once:
            break
        # sleep until next cycle
        for _ in range(int(args.interval*10)):
            if _stop:
                break
            time.sleep(0.1)
        if _stop:
            break

if __name__ == "__main__":
    main()
