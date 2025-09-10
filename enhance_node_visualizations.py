#!/usr/bin/env python3
"""
Enhance node page metrics with improved visualization
This script focuses on enhancing the battery display with a visual progress bar
and adding color-coding to important metrics.
"""

import re
import sys
from pathlib import Path

def enhance_battery_visualization(html_path):
    """
    Enhance battery visualization in a node page HTML file
    
    Args:
        html_path: Path to the node page HTML file
    """
    try:
        # Read the file
        html_content = Path(html_path).read_text(encoding='utf-8')
        
        # Check if this file has already been enhanced
        if '<!-- Battery visualization enhanced -->' in html_content:
            print(f"[INFO] Battery already enhanced: {html_path}")
            return False
            
        # Add CSS for battery visualization in the head section
        battery_css = '''
        <style>
            .battery-bar {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-top: 10px;
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
        <!-- Battery visualization enhanced -->
        '''
        
        html_content = html_content.replace('</head>', f'{battery_css}</head>')
        
        # Find battery metrics in the metrics-grid section
        battery_pattern = r'<div class="metric-card">\s*<div class="metric-name">🔋 Battery</div>\s*<div class="metric-value">(\d+)%</div>\s*</div>'
        battery_match = re.search(battery_pattern, html_content)
        
        if battery_match:
            battery_pct = int(battery_match.group(1))
            
            # Determine the color class based on the battery percentage
            color_class = "battery-critical"
            if battery_pct > 75:
                color_class = "battery-good"
            elif battery_pct > 40:
                color_class = "battery-medium"
            elif battery_pct > 20:
                color_class = "battery-low"
                
            # Create the enhanced battery HTML
            enhanced_battery = f'''<div class="metric-card">
                <div class="metric-name">🔋 Battery</div>
                <div style="margin-top: 10px;">
                    <div class="battery-bar">
                        <div class="battery-visual">
                            <div class="battery-fill {color_class}" style="width: {battery_pct}%"></div>
                        </div>
                        <span>{battery_pct}%</span>
                    </div>
                </div>
            </div>'''
            
            # Replace the original battery card with the enhanced one
            html_content = re.sub(battery_pattern, enhanced_battery, html_content)
            
            # Enhance channel utilization with color coding
            html_content = enhance_metric_color(html_content, r'Channel Utilization', r'(\d+\.?\d*)%', 
                                               lambda val: "#4CAF50" if val < 10 else 
                                                         "#FFEB3B" if val < 25 else 
                                                         "#FF9800" if val < 50 else "#e53935")
            
            # Enhance air utilization with color coding
            html_content = enhance_metric_color(html_content, r'Air TX', r'(\d+\.?\d*)%', 
                                               lambda val: "#4CAF50" if val < 5 else 
                                                         "#FFEB3B" if val < 15 else 
                                                         "#FF9800" if val < 30 else "#e53935")
            
            # Write the updated content back to the file
            Path(html_path).write_text(html_content, encoding='utf-8')
            return True
        else:
            print(f"[WARN] No battery metric found in {html_path}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to enhance battery in {html_path}: {e}")
        return False

def enhance_metric_color(html_content, metric_name, value_pattern, color_func):
    """
    Enhance a metric with color coding based on its value
    
    Args:
        html_content: HTML content to modify
        metric_name: Name of the metric to enhance
        value_pattern: Regex pattern to extract the value
        color_func: Function that takes a value and returns a color
    
    Returns:
        Modified HTML content
    """
    # Find the metric in the metrics-grid section
    metric_pattern = rf'<div class="metric-card">\s*<div class="metric-name">[^<]*{metric_name}[^<]*</div>\s*<div class="metric-value">({value_pattern})</div>\s*</div>'
    
    def replace_metric(match):
        full_match = match.group(0)
        value_str = match.group(1)
        value = float(value_str.strip('%'))
        color = color_func(value)
        
        # Replace the metric value with a colored version
        return full_match.replace(
            f'<div class="metric-value">{value_str}</div>', 
            f'<div class="metric-value" style="color:{color};">{value_str}</div>'
        )
    
    return re.sub(metric_pattern, replace_metric, html_content)

def enhance_all_nodes(plots_dir="plots"):
    """
    Enhance all node pages in the specified directory
    
    Args:
        plots_dir: Path to the plots directory containing node subdirectories
    """
    plots_path = Path(plots_dir)
    enhanced_count = 0
    
    # Find all node directories
    node_dirs = [d for d in plots_path.glob('node_*') if d.is_dir()]
    
    for node_dir in node_dirs:
        # Check for index.html in the node directory
        index_path = node_dir / 'index.html'
        if index_path.exists():
            if enhance_battery_visualization(index_path):
                print(f"[INFO] Enhanced battery visualization in {node_dir.name}")
                enhanced_count += 1
    
    return enhanced_count

def main():
    """Main function"""
    # Get plots directory from command line argument or use default
    plots_dir = "plots"
    if len(sys.argv) > 1:
        plots_dir = sys.argv[1]
    
    print(f"[INFO] Enhancing node visualizations in {plots_dir}")
    enhanced_count = enhance_all_nodes(plots_dir)
    print(f"[INFO] Enhanced visualizations in {enhanced_count} node pages")

if __name__ == "__main__":
    main()
