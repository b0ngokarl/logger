#!/usr/bin/env python3
"""
Test script to verify that the node pages update correctly.
This simulates collecting telemetry and traceroute data and updating node pages.
"""
import sys
from pathlib import Path
from update_node_pages import update_node_pages

def main():
    # Sample node IDs
    node_ids = ["!9eed0410", "!a0cc8008", "!fd17c0ed", "!2df67288"]
    
    # Output directory
    plots_dir = Path("plots")
    plots_dir.mkdir(exist_ok=True)
    
    # Process each node
    for node_id in node_ids:
        print(f"Updating page for {node_id}...")
        
        # Sample telemetry data
        telemetry = {
            "battery_pct": 75.5,
            "voltage_v": 3.8,
            "uptime_s": 86400,  # 24 hours
            "channel_util_pct": 15.2,
            "air_tx_pct": 5.7
        }
        
        # Sample traceroute data (forward and backward paths)
        traceroute = {
            "forward": [
                (node_id, "!abcd1234", -75.5),
                ("!abcd1234", "!efgh5678", -78.2),
            ],
            "back": [
                ("!efgh5678", "!abcd1234", -76.8),
                ("!abcd1234", node_id, -74.3),
            ]
        }
        
        # Update the node page
        output_path = update_node_pages(node_id, telemetry, traceroute, plots_dir)
        print(f"  Created {output_path}")
    
    print("\nDone! Node pages created in the plots/ directory.")
    print("You can view them by opening plots/node_XXXXX/index.html in a browser.")

if __name__ == "__main__":
    main()
