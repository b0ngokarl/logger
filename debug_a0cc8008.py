#!/usr/bin/env python3
"""
Debug script for node !a0cc8008 with verbose output
"""
from pathlib import Path
import re
import sys

def debug_node_page(node_id, output_dir="plots"):
    """Debug a node page with verbose output"""
    node_id_clean = node_id.lstrip('!')
    html_path = Path(output_dir) / f"node_{node_id_clean}" / "index.html"
    
    if not html_path.exists():
        print(f"[ERROR] Node page not found: {html_path}")
        return False
    
    print(f"[DEBUG] Analyzing node page: {html_path}")
    
    with open(html_path, 'r') as file:
        content = file.read()
    
    # Check for Node ID in header
    header_match = re.search(r'<h1>Node\s+!([a-zA-Z0-9]+)\s+Dashboard</h1>', content)
    if header_match:
        print(f"[DEBUG] Node ID in header: {header_match.group(1)}")
    else:
        print("[DEBUG] Node ID not found in header")
    
    # Check for Node ID badge
    badge_match = re.search(r'<div class="node-id-badge">!([a-zA-Z0-9]+)</div>', content)
    if badge_match:
        print(f"[DEBUG] Node ID badge: {badge_match.group(1)}")
    else:
        print("[DEBUG] Node ID badge not found")
    
    # Check for Node ID in table
    table_match = re.search(r'<td><strong>Node ID</strong></td>\s*<td>!([a-zA-Z0-9]+)</td>', content)
    if table_match:
        print(f"[DEBUG] Node ID in table: {table_match.group(1)}")
    else:
        print("[DEBUG] Node ID not found in table")
    
    # Check for battery visualization
    battery_match = re.search(r'<div class="battery-fill battery-[a-z]+" style="width: ([0-9.]+)%', content)
    if battery_match:
        print(f"[DEBUG] Battery visualization: {battery_match.group(1)}%")
    else:
        print("[DEBUG] Battery visualization not found")
    
    # Check for telemetry metrics
    metrics = ["Battery", "Voltage", "Channel Util", "Air Tx", "Uptime"]
    for metric in metrics:
        metric_match = re.search(f'<div class="metric-name">[^<]*{metric}[^<]*</div>', content)
        if metric_match:
            print(f"[DEBUG] Metric found: {metric}")
        else:
            print(f"[DEBUG] Metric not found: {metric}")
    
    # Check for color-coded metrics
    color_match = re.search(r'<span style="color:#([0-9A-F]+);font-weight:bold;">([0-9.]+%)</span>', content)
    if color_match:
        print(f"[DEBUG] Color-coded metric: {color_match.group(2)} with color #{color_match.group(1)}")
    else:
        print("[DEBUG] No color-coded metrics found")
    
    # Check for status indicator
    status_match = re.search(r'<span class="status-indicator status-([a-z]+)">([^<]+)</span>', content)
    if status_match:
        print(f"[DEBUG] Status indicator: {status_match.group(2)} ({status_match.group(1)})")
    else:
        print("[DEBUG] Status indicator not found")
    
    # Check for Last Heard information
    last_heard_match = re.search(r'<td><strong>Last Heard</strong></td>\s*<td>([^<]+)</td>', content)
    if last_heard_match:
        print(f"[DEBUG] Last Heard: {last_heard_match.group(1)}")
    else:
        print("[DEBUG] Last Heard information not found")
    
    print("[DEBUG] Analysis complete")
    return True

if __name__ == "__main__":
    node_id = "!a0cc8008"
    if len(sys.argv) > 1:
        node_id = sys.argv[1]
    
    debug_node_page(node_id)
