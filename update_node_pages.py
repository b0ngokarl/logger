#!/usr/bin/env python3
"""
Create or update node-specific pages with both telemetry and traceroute information.
This script is called by meshtastic_telemetry_logger.py to ensure node-specific pages
are updated after each telemetry/traceroute collection.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Optional

def update_node_pages(node_id, telemetry_data=None, traceroute_data=None, output_dir="plots"):
    """Update HTML page for a specific node with telemetry and traceroute data.
    
    Args:
        node_id: Node ID (can include ! prefix)
        telemetry_data: Dict of telemetry metrics
        traceroute_data: Dict of traceroute information
        output_dir: Output directory for HTML files
        
    Returns:
        Path to the created HTML file
    """
    # Normalize node ID by removing ! prefix for file operations
    normalized_node_id = node_id.strip('!')
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Create node directory if it doesn't exist
    node_dir = os.path.join(output_dir, f"node_{normalized_node_id}")
    if not os.path.exists(node_dir):
        os.makedirs(node_dir)
        print(f"[DEBUG] Created node directory: {node_dir}")
        
    # Create placeholder images for nodes without telemetry data
    # This ensures that all node pages have chart images to display
    if not telemetry_data:
        from PIL import Image, ImageDraw, ImageFont
        try:
            # Create placeholder images
            for img_name in ["battery", "voltage", "channel_util", "air_tx", "uptime_hours"]:
                img_path = os.path.join(node_dir, f"{img_name}.png")
                # Skip if image already exists
                if os.path.exists(img_path):
                    continue
                
                # Create a placeholder image
                img = Image.new('RGB', (800, 400), color=(240, 240, 240))
                d = ImageDraw.Draw(img)
                
                # Try to load a font, or use default if not available
                try:
                    font = ImageFont.truetype("DejaVuSans", 18)
                except Exception:
                    font = ImageFont.load_default()
                
                # Draw no data message
                d.text((400, 200), "No telemetry data available", 
                       fill=(100, 100, 100), anchor="mm", font=font)
                
                # Save the image
                img.save(img_path)
                print(f"[DEBUG] Created placeholder image: {img_path}")
        except Exception as e:
            print(f"[WARN] Could not create placeholder images: {e}", file=sys.stderr)
        
    # Create HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Node {node_id} Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3 {{
            color: #333;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        .node-id {{
            font-weight: bold;
            background-color: #eee;
            padding: 5px 10px;
            border-radius: 4px;
        }}
        .back-link {{
            margin-top: 20px;
            display: block;
        }}
        .metrics {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            width: calc(20% - 15px);
            min-width: 150px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        .metric-name {{
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .charts figure {{
            margin: 0;
            text-align: center;
        }}
        .charts figcaption {{
            margin-bottom: 10px;
            font-weight: bold;
        }}
        .charts img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        
        /* Traceroute styling */
        .traceroute-section {{
            margin-top: 30px;
            border-top: 1px solid #eee;
            padding-top: 20px;
        }}
        .trace-direction {{
            margin-bottom: 20px;
        }}
        .trace-path {{
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 10px;
        }}
        .hop {{
            display: flex;
            align-items: center;
            padding: 10px;
            background-color: #f9f9f9;
            border-radius: 4px;
            margin-bottom: 8px;
        }}
        .hop-num {{
            background-color: #4CAF50;
            color: white;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-weight: bold;
        }}
        .hop-from, .hop-to {{
            font-family: monospace;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 3px;
        }}
        .hop-arrow {{
            margin: 0 10px;
            color: #666;
            font-size: 20px;
        }}
        .hop-db {{
            margin-left: auto;
            font-weight: bold;
            background-color: #e9f5e9;
            padding: 5px 10px;
            border-radius: 4px;
            border-left: 3px solid #4CAF50;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Node Dashboard</h1>
            <div class="node-id">{node_id}</div>
        </div>
        
        """
    
    # Add node information section if available in telemetry data
    if telemetry_data:
        # Print debug info about available fields
        print(f"[DEBUG] Node information fields: {list(telemetry_data.keys())}")
        
        # Check if any node info fields are available that are not just basic telemetry
        node_info_fields = ['user', 'id', 'name', 'aka', 'hardware', 'key', 'firmware', 'latitude', 'longitude', 'altitude', 'signal_strength', 'hops', 'last_seen']
        basic_telemetry_fields = ['battery_pct', 'voltage_v', 'uptime_s', 'channel_util_pct', 'air_tx_pct']
        
        # Check if any node information exists
        node_info_fields = ['user', 'id', 'name', 'aka', 'hardware', 'key', 'firmware', 'latitude', 'longitude', 'altitude', 'signal_strength', 'hops', 'last_seen']
        
        # We need to actually check if any of these fields have data
        has_node_info = False
        for field in node_info_fields:
            if field in telemetry_data and telemetry_data[field] and str(telemetry_data[field]) != 'Unknown' and str(telemetry_data[field]) != 'N/A':
                has_node_info = True
                break
        
        # Debugging information
        print(f"[DEBUG] Has node info: {has_node_info}, telemetry keys: {list(telemetry_data.keys())}, node_info_fields present: {[f for f in node_info_fields if f in telemetry_data]}")
        
        # Start the node info section
        html_content += """
    <div class="node-info-section">
        <h2>Node Information</h2>
        <table class="info-table" style="width:100%; border-collapse:collapse; margin-bottom:20px;">
            <tr>
                <th style="text-align:left; padding:8px; border-bottom:1px solid #ddd; width:25%;">Property</th>
                <th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Value</th>
            </tr>
        """
        
        # If we have no node info, add a default row showing the node ID
        if not has_node_info:
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Node ID</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{node_id}</td>
            </tr>
            """
        
        # Add name if available - prioritize 'user' field over 'id' field
        if 'user' in telemetry_data and telemetry_data['user'] and telemetry_data['user'] != 'Unknown' and telemetry_data['user'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Name</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('user')}</td>
            </tr>
            """
        elif 'id' in telemetry_data and telemetry_data['id'] and telemetry_data['id'] != 'Unknown' and telemetry_data['id'] != 'N/A':
            # Display the ID without the ! prefix for cleaner display
            clean_id = telemetry_data['id'].strip('!') if telemetry_data['id'].startswith('!') else telemetry_data['id']
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>ID</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{clean_id}</td>
            </tr>
            """
        
        # Add AKA if available
        if 'aka' in telemetry_data and telemetry_data['aka'] and telemetry_data['aka'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>AKA</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('aka')}</td>
            </tr>
            """
        
        # Add hardware if available
        if 'hardware' in telemetry_data and telemetry_data['hardware'] and telemetry_data['hardware'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Hardware</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('hardware')}</td>
            </tr>
            """
            
        # Add firmware if available
        if 'firmware' in telemetry_data and telemetry_data['firmware'] and telemetry_data['firmware'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Firmware</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('firmware')}</td>
            </tr>
            """
            
        # Add key if available
        if 'key' in telemetry_data and telemetry_data['key'] and telemetry_data['key'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Key</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('key')}</td>
            </tr>
            """
            
        # Add signal strength if available
        if 'hops' in telemetry_data and telemetry_data['hops'] and telemetry_data['hops'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Signal Strength</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('hops')}</td>
            </tr>
            """
        
        # Add location if available
        if ('latitude' in telemetry_data and telemetry_data['latitude'] and telemetry_data['latitude'] != 'N/A' and
            'longitude' in telemetry_data and telemetry_data['longitude'] and telemetry_data['longitude'] != 'N/A'):
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Location</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">
                    {telemetry_data.get('latitude')}, {telemetry_data.get('longitude')}
                    <a href="https://www.openstreetmap.org/?mlat={telemetry_data.get('latitude').replace('°', '')}&mlon={telemetry_data.get('longitude').replace('°', '')}&zoom=15" target="_blank" style="margin-left:10px; font-size:12px;">(View on Map)</a>
                </td>
            </tr>
            """
        
        # Add signal strength if available
        if 'signal_strength' in telemetry_data and telemetry_data['signal_strength'] and telemetry_data['signal_strength'] != 'N/A':
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Signal Strength</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('signal_strength')}</td>
            </tr>
            """
        
        # Add hops if available
        if 'hops' in telemetry_data and telemetry_data['hops']:
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Hops</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('hops')}</td>
            </tr>
            """
        
        # Add last seen if available
        if 'last_seen' in telemetry_data and telemetry_data['last_seen']:
            html_content += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #ddd;"><strong>Last Seen</strong></td>
                <td style="padding:8px; border-bottom:1px solid #ddd;">{telemetry_data.get('last_seen')}</td>
            </tr>
            """
        
        html_content += """
        </table>
    </div>
    """
    
    # Add telemetry section if data is available
    if telemetry_data:
        html_content += f"""
    <div class="telemetry-section">
        <h2>Telemetry Information</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-name">Battery</div>
                <div class="metric-value">{telemetry_data.get('battery_pct', 'N/A')}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Voltage</div>
                <div class="metric-value">{telemetry_data.get('voltage_v', 'N/A')} V</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Uptime</div>
                <div class="metric-value">{telemetry_data.get('uptime_s', 0) / 3600:.1f} hours</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Channel Util</div>
                <div class="metric-value">{telemetry_data.get('channel_util_pct', 'N/A')}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Air Tx</div>
                <div class="metric-value">{telemetry_data.get('air_tx_pct', 'N/A')}%</div>
            </div>
        </div>
    </div>
    """
    else:
        html_content += """
    <div class="telemetry-section">
        <h2>Telemetry Information</h2>
        <p>No telemetry data available for this node.</p>
    </div>
    """
    
    # Add charts section
    html_content += """
    <div class="charts-section">
        <h2>Charts</h2>
        <div class="charts">
            <figure>
                <figcaption>Battery</figcaption>
                <a href="battery.png"><img src="battery.png" alt="Battery"></a>
            </figure>
            <figure>
                <figcaption>Voltage</figcaption>
                <a href="voltage.png"><img src="voltage.png" alt="Voltage"></a>
            </figure>
            <figure>
                <figcaption>Channel Util</figcaption>
                <a href="channel_util.png"><img src="channel_util.png" alt="Channel Utilization"></a>
            </figure>
            <figure>
                <figcaption>Air Tx</figcaption>
                <a href="air_tx.png"><img src="air_tx.png" alt="Air Transmit"></a>
            </figure>
            <figure>
                <figcaption>Uptime</figcaption>
                <a href="uptime_hours.png"><img src="uptime_hours.png" alt="Uptime"></a>
            </figure>
        </div>
    </div>
    """
    
    # Add traceroute section if data is available
    if traceroute_data:
        html_content += """
    <div class="traceroute-section">
        <h2>Traceroute Information</h2>
    """
        
        # Add forward path
        if traceroute_data.get('forward'):
            html_content += """
        <div class="trace-direction">
            <h3>Forward Path</h3>
            <div class="trace-path">
            """
            
            for i, (src, dest, db) in enumerate(traceroute_data['forward']):
                html_content += f"""
                <div class="hop">
                    <div class="hop-num">{i+1}</div>
                    <div class="hop-from">{src}</div>
                    <div class="hop-arrow">→</div>
                    <div class="hop-to">{dest}</div>
                    <div class="hop-db">{db:.1f} dB</div>
                </div>
                """
            
            html_content += """
            </div>
        </div>
            """
            
        # Add backward path
        if traceroute_data.get('back'):
            html_content += """
        <div class="trace-direction">
            <h3>Reverse Path</h3>
            <div class="trace-path">
            """
            
            for i, (src, dest, db) in enumerate(traceroute_data['back']):
                html_content += f"""
                <div class="hop">
                    <div class="hop-num">{i+1}</div>
                    <div class="hop-from">{src}</div>
                    <div class="hop-arrow">→</div>
                    <div class="hop-to">{dest}</div>
                    <div class="hop-db">{db:.1f} dB</div>
                </div>
                """
            
            html_content += """
            </div>
        </div>
            """
            
        html_content += """
    </div>
        """
    
    # Close HTML
    html_content += """
    <a href="../index.html" class="back-link">← Back to Dashboard</a>
    </div>
</body>
</html>
    """
    
    # Write HTML to file
    index_path = os.path.join(node_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(html_content)
    
    print(f"[DEBUG] Updated node page at {index_path}")
    return index_path


if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) < 2:
        print("Usage: update_node_pages.py [node_id] [optional: output_dir]")
        sys.exit(1)
        
    node_id = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "plots"
    
    # Example telemetry data
    telemetry = {
        "battery_pct": 85.2,
        "voltage_v": 3.8,
        "uptime_s": 12345,
        "channel_util_pct": 12.3,
        "air_tx_pct": 5.7
    }
    
    # Example traceroute data
    traceroute = {
        "forward": [
            ("!abcd1234", "!efgh5678", 3.5),
            ("!efgh5678", "!ijkl9012", 2.8),
        ],
        "back": [
            ("!ijkl9012", "!efgh5678", 3.0),
            ("!efgh5678", "!abcd1234", 2.5),
        ]
    }
    
    path = update_node_pages(node_id, telemetry, traceroute, output_dir)
    print(f"Updated node page at {path}")
