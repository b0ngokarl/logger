#!/usr/bin/env python3
"""
Fix and enhance all node pages for Meshtastic telemetry logger
This script fixes the duplicate Node ID issue, enhances metrics visualization,
and updates example nodes with more realistic data
"""

import re
import sys
from pathlib import Path

def fix_node_page(html_path):
    """
    Fix a node page HTML file to remove duplicate Node ID display
    
    Args:
        html_path: Path to the node page HTML file
    """
    try:
        # Read the file
        html_content = Path(html_path).read_text(encoding='utf-8')
        
        # Check if this file has already been fixed
        if '<!-- Node page fixed -->' in html_content:
            return False
            
        # Remove Node ID from the information table
        # This pattern matches the Node ID row in the information table
        pattern = r'<tr>\s*<th>Node ID</th>\s*<td>[^<]*</td>\s*</tr>'
        html_content = re.sub(pattern, '', html_content)
        
        # Add a marker that this file has been fixed
        html_content = html_content.replace('</head>', '<!-- Node page fixed -->\n</head>')
        
        # Write the updated content back to the file
        Path(html_path).write_text(html_content, encoding='utf-8')
        return True
    except Exception as e:
        print(f"[ERROR] Failed to fix node page {html_path}: {e}")
        return False

def enhance_metric_visualization(html_path):
    """
    Enhance metric visualization in a node page HTML file
    
    Args:
        html_path: Path to the node page HTML file
    """
    try:
        # Read the file
        html_content = Path(html_path).read_text(encoding='utf-8')
        
        # Check if this file has already been enhanced
        if '<!-- Metrics enhanced -->' in html_content:
            return False
            
        # Find the telemetry information section
        telemetry_section_match = re.search(r'<h2>📊\s*Telemetry Information</h2>(.*?)<div class="section">', html_content, re.DOTALL)
        if not telemetry_section_match:
            return False
            
        telemetry_section = telemetry_section_match.group(1)
        
        # Extract all metric cards
        metric_cards = re.findall(r'<div class="metric-card">(.*?)</div>', telemetry_section, re.DOTALL)
        enhanced_section = telemetry_section
        
        # Enhance battery metric with a visual bar
        for card in metric_cards:
            metric_name_match = re.search(r'<div class="metric-name">(.*?)</div>', card)
            metric_value_match = re.search(r'<div class="metric-value">(.*?)</div>', card)
            
            if not metric_name_match or not metric_value_match:
                continue
                
            metric_name = metric_name_match.group(1)
            metric_value = metric_value_match.group(1)
            
            # Enhance battery display with a visual bar
            if '🔋 Battery' in metric_name and '%' in metric_value:
                try:
                    battery_pct = int(metric_value.replace('%', '').strip())
                    
                    # Determine the color based on the battery level
                    color_class = "battery-critical"
                    if battery_pct > 75:
                        color_class = "battery-good"
                    elif battery_pct > 40:
                        color_class = "battery-medium"
                    elif battery_pct > 20:
                        color_class = "battery-low"
                        
                    # Create the enhanced battery bar HTML
                    enhanced_battery = f'''
                    <div class="metric-name">{metric_name}</div>
                    <div style="margin-top: 10px;">
                        <div class="battery-bar">
                            <div class="battery-visual">
                                <div class="battery-fill {color_class}" style="width: {battery_pct}%"></div>
                            </div>
                            <span>{battery_pct}%</span>
                        </div>
                    </div>
                    '''
                    
                    # Replace the original card with the enhanced one
                    enhanced_section = enhanced_section.replace(card, enhanced_battery)
                    
                except ValueError:
                    pass
                    
            # Enhance channel utilization display with color indicators
            elif 'Channel Utilization' in metric_name and '%' in metric_value:
                try:
                    util_pct = float(metric_value.replace('%', '').strip())
                    color = "#4CAF50"  # Good/green
                    
                    if util_pct > 50:
                        color = "#e53935"  # Critical/red
                    elif util_pct > 25:
                        color = "#FF9800"  # Warning/orange
                    elif util_pct > 10:
                        color = "#FFEB3B"  # Attention/yellow
                        
                    enhanced_value = f'<div class="metric-value" style="color:{color};">{metric_value}</div>'
                    enhanced_card = card.replace(f'<div class="metric-value">{metric_value}</div>', enhanced_value)
                    enhanced_section = enhanced_section.replace(card, enhanced_card)
                    
                except ValueError:
                    pass
                    
            # Enhance signal strength display with color indicators
            elif 'Signal Strength' in metric_name and 'dB' in metric_value:
                try:
                    signal_db = float(metric_value.replace('dB', '').strip())
                    color = "#4CAF50"  # Good/green
                    
                    if signal_db < -90:
                        color = "#e53935"  # Critical/red
                    elif signal_db < -80:
                        color = "#FF9800"  # Warning/orange
                    elif signal_db < -70:
                        color = "#FFEB3B"  # Attention/yellow
                        
                    enhanced_value = f'<div class="metric-value" style="color:{color};font-weight:bold;">{metric_value}</div>'
                    enhanced_card = card.replace(f'<div class="metric-value">{metric_value}</div>', enhanced_value)
                    enhanced_section = enhanced_section.replace(card, enhanced_card)
                    
                except ValueError:
                    pass
        
        # Add CSS for battery visualization
        battery_css = '''
        <style>
            .battery-bar {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .battery-visual {
                height: 24px;
                width: 100%;
                background-color: #f0f0f0;
                border-radius: 12px;
                overflow: hidden;
            }
            .battery-fill {
                height: 100%;
                border-radius: 12px;
                transition: width 0.5s ease;
            }
            .battery-good {
                background: linear-gradient(90deg, #4CAF50, #8BC34A);
            }
            .battery-medium {
                background: linear-gradient(90deg, #FFC107, #FFEB3B);
            }
            .battery-low {
                background: linear-gradient(90deg, #FF9800, #FFC107);
            }
            .battery-critical {
                background: linear-gradient(90deg, #F44336, #FF5252);
            }
        </style>
        '''
        
        # Replace the telemetry section with the enhanced version
        html_content = html_content.replace(telemetry_section, enhanced_section)
        
        # Add the battery CSS before the closing </head> tag
        html_content = html_content.replace('</head>', f'{battery_css}\n<!-- Metrics enhanced -->\n</head>')
        
        # Write the updated content back to the file
        Path(html_path).write_text(html_content, encoding='utf-8')
        return True
    except Exception as e:
        print(f"[ERROR] Failed to enhance metrics in {html_path}: {e}")
        return False

def update_example_nodes(plots_dir):
    """
    Update example node pages with more realistic data
    
    Args:
        plots_dir: Path to the plots directory containing node subdirectories
    """
    plots_path = Path(plots_dir)
    updated_count = 0
    
    # Define example node data
    example_data = {
        "exampleA": {
            "name": "Base Station Alpha",
            "user": "Alice Johnson",
            "hardware": "TTGO T-Beam",
            "firmware": "2.1.22",
            "location": "40.7128° N, 74.0060° W",
            "altitude": "28 m",
            "last_seen": "2025-09-09 20:00:37 UTC",
            "signal": "-62 dB",
            "status": "🔴 Offline (24+ hours)",
            "battery": "57%"
        },
        "exampleB": {
            "name": "Field Repeater Beta",
            "user": "Bob Smith",
            "hardware": "Heltec LoRa32",
            "firmware": "2.1.20",
            "location": "38.8977° N, 77.0365° W",
            "altitude": "15 m",
            "last_seen": "2025-09-09 22:15:42 UTC",
            "signal": "-73 dB",
            "status": "🟢 Online",
            "battery": "82%"
        },
        "exampleC": {
            "name": "Mobile Tracker Charlie",
            "user": "Carol Williams",
            "hardware": "RAK4631 WisBlock",
            "firmware": "2.1.18",
            "location": "34.0522° N, 118.2437° W",
            "altitude": "93 m",
            "last_seen": "2025-09-09 18:30:15 UTC",
            "signal": "-85 dB",
            "status": "🟡 Stale (8+ hours)",
            "battery": "35%"
        },
        "exampleD": {
            "name": "Environmental Monitor Delta",
            "user": "David Miller",
            "hardware": "LilyGO T-Beam v1.1",
            "firmware": "2.1.21",
            "location": "42.3601° N, 71.0589° W",
            "altitude": "43 m",
            "last_seen": "2025-09-09 21:45:09 UTC",
            "signal": "-68 dB",
            "status": "🟢 Online",
            "battery": "91%"
        }
    }
    
    # Find all example node directories
    for node_id, node_data in example_data.items():
        node_dir = plots_path / f"node_{node_id}"
        if not node_dir.exists():
            continue
            
        index_path = node_dir / "index.html"
        if not index_path.exists():
            continue
            
        try:
            # Read the file
            html_content = index_path.read_text(encoding='utf-8')
            
            # Update node information
            for field, value in node_data.items():
                # Skip empty values
                if not value:
                    continue
                
                # Update name in title
                if field == "name":
                    html_content = re.sub(r'<h1>.*?</h1>', f'<h1>{value} ({node_id})</h1>', html_content)
                    
                # Update user in header
                if field == "user":
                    html_content = re.sub(r'<p>Operated by .*?•', f'<p>Operated by {value} •', html_content)
                    
                # Update various fields in the info table
                if field in ["hardware", "firmware", "location", "altitude"]:
                    field_label = field.title()
                    # Match the field in the table and replace its value
                    pattern = f'<tr>\\s*<th>{field_label}</th>\\s*<td>.*?</td>\\s*</tr>'
                    replacement = f'<tr><th>{field_label}</th><td>{value}</td></tr>'
                    html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE | re.DOTALL)
                
                # Update signal strength
                if field == "signal":
                    html_content = re.sub(r'<tr>\s*<th>Signal Strength</th>\s*<td>.*?</td>\s*</tr>', 
                                         f'<tr><th>Signal Strength</th><td><span style="color:#4CAF50;font-weight:bold;">{value}</span></td></tr>', 
                                         html_content, 
                                         flags=re.IGNORECASE | re.DOTALL)
                
                # Update status
                if field == "status":
                    status_style = "background-color:#d4edda;color:#155724" if "Online" in value else "background-color:#f8d7da;color:#721c24"
                    html_content = re.sub(r'<tr>\s*<th>Status</th>\s*<td>.*?</td>\s*</tr>',
                                         f'<tr><th>Status</th><td><span style="{status_style};padding:3px 8px;border-radius:3px;">{value}</span></td></tr>',
                                         html_content,
                                         flags=re.IGNORECASE | re.DOTALL)
                
                # Update battery in metrics section
                if field == "battery" and "%" in value:
                    try:
                        battery_pct = int(value.replace('%', '').strip())
                        battery_html = f'<div class="metric-value">{battery_pct}%</div>'
                        html_content = re.sub(r'<div class="metric-name">🔋\s*Battery</div>\s*<div class="metric-value">.*?</div>',
                                             f'<div class="metric-name">🔋 Battery</div>\n{battery_html}',
                                             html_content,
                                             flags=re.IGNORECASE | re.DOTALL)
                    except ValueError:
                        pass
            
            # Write the updated content back to the file
            index_path.write_text(html_content, encoding='utf-8')
            updated_count += 1
            
        except Exception as e:
            print(f"[ERROR] Failed to update example node {node_id}: {e}")
    
    return updated_count

def process_node_pages(plots_dir):
    """
    Process all node pages in a directory
    
    Args:
        plots_dir: Path to the plots directory containing node subdirectories
    """
    plots_path = Path(plots_dir)
    fixed_count = 0
    enhanced_count = 0
    
    print(f"[INFO] Processing node pages in {plots_dir}")
    
    # Find all node directories
    node_dirs = [d for d in plots_path.glob('node_*') if d.is_dir()]
    
    for node_dir in node_dirs:
        # Check for index.html in the node directory
        index_path = node_dir / 'index.html'
        if not index_path.exists():
            continue
            
        # Fix node pages (remove duplicate Node ID)
        if fix_node_page(index_path):
            fixed_count += 1
            
        # Enhance metric visualization
        if enhance_metric_visualization(index_path):
            enhanced_count += 1
    
    # Update example nodes with realistic data
    updated_count = update_example_nodes(plots_path)
    
    print(f"[INFO] Fixed {fixed_count} node pages")
    print(f"[INFO] Enhanced {enhanced_count} node pages with improved visualizations")
    print(f"[INFO] Updated {updated_count} example nodes with realistic data")
    
    return fixed_count, enhanced_count, updated_count

def main():
    """Main function for processing node pages"""
    plots_dir = "plots"  # Default plots directory
    
    # Check if a different plots directory is specified
    if len(sys.argv) > 1:
        plots_dir = sys.argv[1]
    
    # Process node pages in the specified directory
    process_node_pages(plots_dir)

if __name__ == "__main__":
    main()
