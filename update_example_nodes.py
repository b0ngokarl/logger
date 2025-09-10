#!/usr/bin/env python3
"""
Update example node pages with realistic information.

This script:
1. Updates the example node pages with realistic node information
2. Makes them more presentable for demonstration purposes
3. Removes duplicate Node ID display
4. Enhances metric visualization
"""
import os
import sys
import re
from pathlib import Path

# Example node data with realistic information
EXAMPLE_NODES = {
    "exampleA": {
        "name": "Base Station Alpha",
        "user": "Alice Johnson",
        "hardware": "TTGO T-Beam",
        "firmware": "2.1.22",
        "location": "40.7128° N, 74.0060° W",
        "altitude": "10m",
        "signal": "-65 dB",
        "hops": "1",
        "battery": "92%",
        "voltage": "3.85V",
        "channel_util": "0.3%",
        "air_tx": "0.1%",
        "uptime": "2.0 hours"
    },
    "exampleB": {
        "name": "Waypoint Station",
        "user": "John Smith",
        "hardware": "T-Beam v1.1",
        "firmware": "2.1.22",
        "location": "48.1375° N, 11.5750° E",
        "altitude": "520m",
        "signal": "-72 dB",
        "hops": "2",
        "battery": "85%",
        "voltage": "3.78V",
        "channel_util": "0.5%",
        "air_tx": "0.2%",
        "uptime": "1.0 hour"
    },
    "exampleC": {
        "name": "Field Node 1",
        "user": "Robert Davis",
        "hardware": "Heltec v2",
        "firmware": "2.1.20",
        "location": "51.5074° N, 0.1278° W",
        "altitude": "15m",
        "signal": "-78 dB",
        "hops": "3",
        "battery": "75%",
        "voltage": "3.65V",
        "channel_util": "2.1%",
        "air_tx": "1.8%",
        "uptime": "4.0 hours"
    },
    "exampleD": {
        "name": "Mobile Unit Delta",
        "user": "Sarah Wilson",
        "hardware": "LilyGO T-Echo",
        "firmware": "2.1.21",
        "location": "34.0522° N, 118.2437° W",
        "altitude": "95m",
        "signal": "-82 dB",
        "hops": "4",
        "battery": "64%",
        "voltage": "3.55V",
        "channel_util": "4.5%",
        "air_tx": "3.2%",
        "uptime": "6.0 hours"
    }
}

def update_example_node(node_id, data, output_dir="plots"):
    """Update an example node page with realistic information."""
    node_dir = os.path.join(output_dir, f"node_{node_id}")
    if not os.path.exists(node_dir):
        print(f"[ERROR] Node directory not found: {node_dir}")
        return False
    
    html_path = os.path.join(node_dir, "index.html")
    if not os.path.exists(html_path):
        print(f"[ERROR] Node HTML file not found: {html_path}")
        return False
    
    # Create improved HTML with realistic information
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Node !{node_id} - {data['name']}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 20px auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            padding: 30px;
            text-align: center;
            position: relative;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .node-badge {{
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-family: monospace;
            font-weight: bold;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #2196F3;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .info-table th, .info-table td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        .info-table th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
            width: 30%;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #f8f9fa, #ffffff);
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .metric-name {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        .metric-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2196F3;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        .chart-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        .chart-image {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 6px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            padding: 4px;
            background: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{data['name']} ({node_id})</h1>
            <p>Operated by {data['user']} • Last seen: 2025-09-09 20:00:37 UTC</p>
            <div class="node-badge">!{node_id}</div>
        </div>
        
        <div class="content">
            <div class="section">
                <h2>📋 Node Information</h2>
                <table class="info-table">
                    <tr>
                        <th>Node ID</th>
                        <td>!{node_id}</td>
                    </tr>
                    <tr>
                        <th>Name</th>
                        <td>{data['name']}</td>
                    </tr>
                    <tr>
                        <th>User/Operator</th>
                        <td>{data['user']}</td>
                    </tr>
                    <tr>
                        <th>Hardware</th>
                        <td>{data['hardware']}</td>
                    </tr>
                    <tr>
                        <th>Firmware</th>
                        <td>{data['firmware']}</td>
                    </tr>
                    <tr>
                        <th>Location</th>
                        <td>
                            {data['location']}
                            <br><a href="#" style="font-size:0.9em;color:#2196F3;">📍 View on Map</a>
                        </td>
                    </tr>
                    <tr>
                        <th>Altitude</th>
                        <td>{data['altitude']}</td>
                    </tr>
                    <tr>
                        <th>Signal Strength</th>
                        <td>{data['signal']}</td>
                    </tr>
                    <tr>
                        <th>Hop Count</th>
                        <td>{data['hops']} hops</td>
                    </tr>
                </table>
            </div>
            
            <div class="section">
                <h2>📊 Telemetry Information</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-name">🔋 Battery</div>
                        <div class="metric-value">{data['battery']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">⚡ Voltage</div>
                        <div class="metric-value">{data['voltage']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">📡 Channel Utilization</div>
                        <div class="metric-value">{data['channel_util']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">📤 Air TX</div>
                        <div class="metric-value">{data['air_tx']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-name">⏱️ Uptime</div>
                        <div class="metric-value">{data['uptime']}</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📈 Charts</h2>
                <div class="charts-grid">
                    <div class="chart-card">
                        <h3>🔋 Battery Level</h3>
                        <a href="battery.png">
                            <img src="battery.png" alt="Battery" class="chart-image">
                        </a>
                    </div>
                    <div class="chart-card">
                        <h3>⚡ Voltage</h3>
                        <a href="voltage.png">
                            <img src="voltage.png" alt="Voltage" class="chart-image">
                        </a>
                    </div>
                    <div class="chart-card">
                        <h3>📡 Channel Utilization</h3>
                        <a href="channel_util.png">
                            <img src="channel_util.png" alt="Channel Util" class="chart-image">
                        </a>
                    </div>
                    <div class="chart-card">
                        <h3>📤 Air Transmit</h3>
                        <a href="air_tx.png">
                            <img src="air_tx.png" alt="Air TX" class="chart-image">
                        </a>
                    </div>
                    <div class="chart-card">
                        <h3>⏱️ Uptime</h3>
                        <a href="uptime_hours.png">
                            <img src="uptime_hours.png" alt="Uptime" class="chart-image">
                        </a>
                    </div>
                </div>
            </div>
        </div>
        
        <div style="padding: 20px; text-align: center;">
            <a href="../index.html" style="display:inline-block;padding:10px 20px;background:#2196F3;color:white;text-decoration:none;border-radius:5px;">← Back to Main Dashboard</a>
        </div>
    </div>
</body>
</html>"""
    
    # Write the HTML file
    try:
        with open(html_path, 'w') as f:
            f.write(html)
        print(f"[SUCCESS] Updated example node {node_id} with realistic information")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write HTML file: {e}")
        return False

def main():
    """Update all example nodes."""
    # Check if plots directory is provided as an argument
    output_dir = "plots"
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]

    print(f"[INFO] Updating example nodes in {output_dir}")
    success_count = 0
    
    for node_id, data in EXAMPLE_NODES.items():
        if update_example_node(node_id, data, output_dir):
            success_count += 1
    
    print(f"Updated {success_count} of {len(EXAMPLE_NODES)} example nodes")
    
    # Also fix duplicate Node ID display and enhance metrics if fix_all_node_pages.py exists
    if os.path.exists("fix_all_node_pages.py"):
        print("[INFO] Applying fixes and enhancements to example node pages")
        try:
            import subprocess
            subprocess.run(["python3", "fix_all_node_pages.py", output_dir], check=True)
            print("[INFO] Successfully applied fixes and enhancements")
        except Exception as e:
            print(f"[ERROR] Failed to apply fixes and enhancements: {e}")
    return 0 if success_count == len(EXAMPLE_NODES) else 1

if __name__ == "__main__":
    sys.exit(main())
