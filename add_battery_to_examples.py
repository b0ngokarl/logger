#!/usr/bin/env python3
"""
Add battery metrics to example node pages
"""

import sys
import re
from pathlib import Path

def add_battery_metric(html_path, battery_pct=85):
    """
    Add a battery metric to the metrics section of a node page
    
    Args:
        html_path: Path to the node page HTML file
        battery_pct: Battery percentage to set (default: 85)
    """
    try:
        # Read the file
        html_content = Path(html_path).read_text(encoding='utf-8')
        
        # Check if this file already has telemetry data
        if '<div class="metric-card">' in html_content:
            print(f"[INFO] Page already has metrics: {html_path}")
            return False
            
        # Find the telemetry section
        telemetry_pattern = r'<div class="section">\s*<h2>📊 Telemetry Information</h2>\s*<p><em>No telemetry data available for this node\.</em></p>\s*</div>'
        
        # Replace the empty telemetry section with one containing metrics
        metrics_section = f'''<div class="section">
            <h2>📊 Telemetry Information</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-name">🔋 Battery</div>
                    <div class="metric-value">{battery_pct}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-name">� Channel Utilization</div>
                    <div class="metric-value">8.2%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-name">📤 Air TX</div>
                    <div class="metric-value">3.5%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-name">⏱️ Uptime</div>
                    <div class="metric-value">72.5 h</div>
                </div>
            </div>
        </div>'''
        
        # Replace the telemetry section
        new_html_content = re.sub(telemetry_pattern, metrics_section, html_content)
        
        if new_html_content != html_content:
            # Write the updated content back to the file
            Path(html_path).write_text(new_html_content, encoding='utf-8')
            print(f"[INFO] Added metrics to {html_path}")
            return True
        else:
            print(f"[WARN] Could not find telemetry section in {html_path}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to add battery metric to {html_path}: {e}")
        return False

def main():
    """Main function"""
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description="Add battery metrics to node pages")
    parser.add_argument("--output-dir", default="plots", help="Output directory")
    parser.add_argument("--node", help="Specific node ID to update (without ! prefix)")
    parser.add_argument("--battery", type=int, default=85, help="Battery percentage (1-100)")
    args = parser.parse_args()
    
    plots_path = Path(args.output_dir)
    added_count = 0
    
    # Process specific node if provided
    if args.node:
        # Normalize node ID (remove ! prefix if present)
        node_id = args.node.lstrip('!')
        index_path = plots_path / f"node_{node_id}" / "index.html"
        if index_path.exists():
            if add_battery_metric(index_path, args.battery):
                added_count += 1
                print(f"[INFO] Added battery metric ({args.battery}%) to node_{node_id}")
    else:
        # Process example nodes
        example_nodes = ["exampleA", "exampleB", "exampleC", "exampleD"]
        
        for node_id in example_nodes:
            # Check for index.html in the node directory
            index_path = plots_path / f"node_{node_id}" / "index.html"
            if index_path.exists():
                # Add different battery levels to each example
                battery_levels = {
                    "exampleA": 95,
                    "exampleB": 75,
                    "exampleC": 35,
                    "exampleD": 15
                }
                
                if add_battery_metric(index_path, battery_levels.get(node_id, 85)):
                    added_count += 1
    
    print(f"[INFO] Added battery metrics to {added_count} node pages")

if __name__ == "__main__":
    main()
