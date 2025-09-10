#!/usr/bin/env python3
"""
Create or update node-specific pages with both telemetry and traceroute information.
This script is called by meshtastic_telemetry_logger.py to ensure node-specific pages
are updated after each telemetry/traceroute collection.

Updated to use standardized HTML templates for consistent styling across all pages.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Optional

# Add core module to path for template imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))
try:
    from html_templates import get_html_template, format_value, create_battery_bar, create_status_indicator
except ImportError:
    # Fallback if import fails
    print("[WARN] Could not import html_templates, using basic styling", file=sys.stderr)

def update_node_pages(node_id, telemetry_data=None, traceroute_data=None, output_dir="plots"):
    """Update HTML page for a specific node with telemetry and traceroute data.
    
    Args:
        node_id: Node ID (can include ! prefix)
        telemetry_data: Dict of telemetry metrics and node information
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
    _create_placeholder_images(node_dir, telemetry_data)
    
    # Build the HTML content using the standardized template
    content = _build_node_content(node_id, telemetry_data, traceroute_data)
    
    # Navigation links for node pages
    navigation = [
        {'url': '../index.html', 'text': '🏠 Main Dashboard'},
        {'url': '../nodes.html', 'text': '🌐 All Nodes'},
        {'url': '../dashboards.html', 'text': '📊 Node Dashboards'},
        {'url': '../diagnostics.html', 'text': '🔍 Diagnostics'}
    ]
    
    # Use standardized HTML template if available, otherwise fallback
    try:
        html_content = get_html_template(
            title=f"Node {node_id} Dashboard",
            content=content,
            node_id=node_id,
            navigation_links=navigation
        )
    except NameError:
        # Fallback to basic HTML if template import failed
        html_content = _fallback_html_template(node_id, content)
    
    # Write HTML to file
    index_path = os.path.join(node_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"[DEBUG] Updated node page at {index_path}")
    return index_path

def _create_placeholder_images(node_dir, telemetry_data):
    """Create placeholder images for nodes without telemetry data."""
    if telemetry_data:
        return  # Skip if we have telemetry data
        
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        for img_name in ["battery", "voltage", "channel_util", "air_tx", "uptime_hours"]:
            img_path = os.path.join(node_dir, f"{img_name}.png")
            if os.path.exists(img_path):
                continue
                
            img = Image.new('RGB', (800, 400), color=(240, 240, 240))
            d = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("DejaVuSans", 18)
            except Exception:
                font = ImageFont.load_default()
            
            d.text((400, 200), "No telemetry data available", 
                   fill=(100, 100, 100), anchor="mm", font=font)
            
            img.save(img_path)
            print(f"[DEBUG] Created placeholder image: {img_path}")
    except Exception as e:
        print(f"[WARN] Could not create placeholder images: {e}", file=sys.stderr)

def _build_node_content(node_id, telemetry_data, traceroute_data):
    """Build the main content for a node page using standardized components."""
    content_parts = []
    
    # Add node information section
    content_parts.append(_build_node_info_section(node_id, telemetry_data))
    
    # Add telemetry metrics section
    content_parts.append(_build_telemetry_section(telemetry_data))
    
    # Add charts section
    content_parts.append(_build_charts_section())
    
    # Add traceroute section if available
    if traceroute_data:
        content_parts.append(_build_traceroute_section(traceroute_data))
    
    return '\n'.join(content_parts)

def _build_node_info_section(node_id, telemetry_data):
    """Build the node information section with all available data."""
    if not telemetry_data:
        return f"""
        <div class="section">
            <h2>Node Information</h2>
            <table class="info-table">
                <tr>
                    <th style="width: 25%;">Property</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td><strong>Node ID</strong></td>
                    <td>{node_id}</td>
                </tr>
            </table>
        </div>
        """
    
    print(f"[DEBUG] Node information fields: {list(telemetry_data.keys())}")
    
    # Define all possible node info fields
    info_fields = [
        ('user', 'Name/User'),
        # Removed duplicate 'Node ID' field here - we'll handle it manually
        ('aka', 'Also Known As'),
        ('hardware', 'Hardware'),
        ('firmware', 'Firmware'),
        ('key', 'Encryption Key'),
        ('latitude', 'Latitude'),
        ('longitude', 'Longitude'),
        ('altitude', 'Altitude'),
        ('signal_strength', 'Signal Strength'),
        ('hops', 'Hop Count'),
        ('last_seen', 'Last Seen')
    ]
    
    # Build table rows for all available information
    rows = []
    
    # Always show the node ID
    rows.append(f"""
        <tr>
            <td><strong>Node ID</strong></td>
            <td>{node_id}</td>
        </tr>
    """)
    
    # Add all other available fields
    for field_key, field_label in info_fields:
        if field_key in telemetry_data and telemetry_data[field_key]:
            value = telemetry_data[field_key]
            
            # Special handling for different value types
            try:
                # Skip 'id' field since we handle it manually at the top to prevent duplication
                if field_key == 'id':
                    continue
                elif field_key in ['latitude', 'longitude'] and 'latitude' in telemetry_data and 'longitude' in telemetry_data:
                    # For location, create a combined row with map link
                    if field_key == 'latitude':  # Only process once for lat/lon pair
                        lat = str(telemetry_data.get('latitude', '')).replace('°', '')
                        lon = str(telemetry_data.get('longitude', '')).replace('°', '')
                        if lat and lon and lat != 'N/A' and lon != 'N/A':
                            map_link = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15"
                            rows.append(f"""
                                <tr>
                                    <td><strong>Location</strong></td>
                                    <td>
                                        {telemetry_data.get('latitude')}, {telemetry_data.get('longitude')}
                                        <br><a href="{map_link}" target="_blank" style="font-size: 0.9em; color: #2196F3;">📍 View on Map</a>
                                    </td>
                                </tr>
                            """)
                    continue  # Skip individual lat/lon processing
                elif field_key == 'signal_strength':
                    try:
                        value = format_value(value, 'signal')
                    except:
                        pass
                elif field_key == 'hops':
                    try:
                        value = f"{int(value)} hops"
                    except:
                        pass
                
                # Skip empty or placeholder values
                if str(value) not in ['', 'Unknown', 'N/A', 'null']:
                    formatted_value = format_value(value) if 'format_value' in globals() else str(value)
                    rows.append(f"""
                        <tr>
                            <td><strong>{field_label}</strong></td>
                            <td>{formatted_value}</td>
                        </tr>
                    """)
            except Exception as e:
                print(f"[DEBUG] Error processing field {field_key}: {e}")
    
    # Build status indicator
    status = create_status_indicator(telemetry_data.get('last_seen')) if 'create_status_indicator' in globals() else None
    if status:
        status_html = f'<span class="status-indicator {status["class"]}">{status["emoji"]} {status["text"]}</span>'
        rows.append(f"""
            <tr>
                <td><strong>Status</strong></td>
                <td>{status_html}</td>
            </tr>
        """)
    
    return f"""
    <div class="section">
        <h2>📋 Node Information</h2>
        <table class="info-table">
            <thead>
                <tr>
                    <th style="width: 25%;">Property</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """

def _build_telemetry_section(telemetry_data):
    """Build the telemetry metrics section with visual indicators."""
    if not telemetry_data:
        return """
        <div class="section">
            <h2>📊 Telemetry Information</h2>
            <p><em>No telemetry data available for this node.</em></p>
        </div>
        """
    
    # Build telemetry metrics cards
    metrics_html = []
    
    # Battery with visual bar
    if 'battery_pct' in telemetry_data and telemetry_data['battery_pct'] is not None:
        battery_html = create_battery_bar(telemetry_data['battery_pct']) if 'create_battery_bar' in globals() else format_value(telemetry_data['battery_pct'], 'percent')
        metrics_html.append(f"""
            <div class="metric-card">
                <div class="metric-name">🔋 Battery</div>
                <div style="margin-top: 10px;">{battery_html}</div>
            </div>
        """)
    
    # Other telemetry metrics
    metrics = [
        ('voltage_v', '⚡ Voltage', 'voltage'),
        ('uptime_s', '⏱️ Uptime', 'time'),
        ('channel_util_pct', '📡 Channel Util', 'channel_util_percent'),  # Changed to specific type for channel util
        ('air_tx_pct', '📤 Air Tx', 'air_tx_percent')  # Changed to specific type for air tx
    ]
    
    for field_key, field_label, value_type in metrics:
        if field_key in telemetry_data and telemetry_data[field_key] is not None:
            formatted_value = format_value(telemetry_data[field_key], value_type) if 'format_value' in globals() else str(telemetry_data[field_key])
            metrics_html.append(f"""
                <div class="metric-card">
                    <div class="metric-name">{field_label}</div>
                    <div class="metric-value">{formatted_value}</div>
                </div>
            """)
    
    return f"""
    <div class="section">
        <h2>📊 Telemetry Information</h2>
        <div class="metrics-grid">
            {''.join(metrics_html)}
        </div>
    </div>
    """

def _build_charts_section():
    """Build the charts section with all telemetry chart images."""
    charts = [
        ('battery.png', '🔋 Battery Level'),
        ('voltage.png', '⚡ Voltage'),
        ('channel_util.png', '📡 Channel Utilization'),
        ('air_tx.png', '📤 Air Transmit'),
        ('uptime_hours.png', '⏱️ Uptime')
    ]
    
    chart_cards = []
    for img_file, chart_title in charts:
        chart_cards.append(f"""
            <div class="chart-card">
                <h3>{chart_title}</h3>
                <a href="{img_file}">
                    <img src="{img_file}" alt="{chart_title}" class="chart-image">
                </a>
            </div>
        """)
    
    return f"""
    <div class="section">
        <h2>📈 Charts</h2>
        <div class="charts-grid">
            {''.join(chart_cards)}
        </div>
    </div>
    """

def _build_traceroute_section(traceroute_data):
    """Build the traceroute section with path visualization."""
    sections = []
    
    # Forward path
    if traceroute_data.get('forward'):
        hops_html = []
        for i, (src, dest, db) in enumerate(traceroute_data['forward']):
            hops_html.append(f"""
                <div class="hop">
                    <div class="hop-num">{i+1}</div>
                    <div class="hop-node">{src}</div>
                    <div class="hop-arrow">→</div>
                    <div class="hop-node">{dest}</div>
                    <div class="hop-signal">{db:.1f} dB</div>
                </div>
            """)
        
        sections.append(f"""
            <h3>🔄 Forward Path</h3>
            <div class="trace-path">
                {''.join(hops_html)}
            </div>
        """)
    
    # Reverse path
    if traceroute_data.get('back'):
        hops_html = []
        for i, (src, dest, db) in enumerate(traceroute_data['back']):
            hops_html.append(f"""
                <div class="hop">
                    <div class="hop-num">{i+1}</div>
                    <div class="hop-node">{src}</div>
                    <div class="hop-arrow">→</div>
                    <div class="hop-node">{dest}</div>
                    <div class="hop-signal">{db:.1f} dB</div>
                </div>
            """)
        
        sections.append(f"""
            <h3>🔙 Reverse Path</h3>
            <div class="trace-path">
                {''.join(hops_html)}
            </div>
        """)
    
    return f"""
    <div class="section traceroute-section">
        <h2>🗺️ Network Routing</h2>
        {''.join(sections)}
    </div>
    """ if sections else ""

def _fallback_html_template(node_id, content):
    """Fallback HTML template if the standardized template import fails."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Node {node_id} Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1, h2 {{ color: #333; }}
        .section {{ margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Node {node_id} Dashboard</h1>
        {content}
        <p><a href="../index.html">← Back to Dashboard</a></p>
    </div>
</body>
</html>"""


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
