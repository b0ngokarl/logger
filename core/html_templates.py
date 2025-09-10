#!/usr/bin/env python3
"""
Shared HTML templates and CSS styles for consistent Meshtastic logger dashboard pages.
This module provides standardized styling and templates to ensure all HTML files
have the same look and feel while containing all available information.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

def get_standard_css() -> str:
    """
    Returns standardized CSS that will be used across all HTML pages
    for consistent styling and modern responsive design.
    """
    return """
        * { 
            box-sizing: border-box; 
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            min-height: calc(100vh - 40px);
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .header {
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            padding: 30px;
            text-align: center;
            position: relative;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .node-id-badge {
            position: absolute;
            top: 30px;
            right: 30px;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 20px;
            font-family: monospace;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .navigation {
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
        }
        
        .nav-link {
            display: inline-block;
            padding: 12px 20px;
            background: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 25px;
            margin: 5px;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .nav-link:hover {
            background: #1976D2;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .section h2 {
            margin-top: 0;
            color: #333;
            font-size: 1.5em;
            border-bottom: 2px solid #2196F3;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #f8f9fa, #ffffff);
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        
        .metric-name {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #2196F3;
        }
        
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .info-table th,
        .info-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        
        .info-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        .info-table tr:hover {
            background: #f8f9fa;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .chart-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .chart-card h3 {
            margin-top: 0;
            color: #333;
            font-size: 1.2em;
            margin-bottom: 15px;
        }
        
        .chart-image {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 6px;
            transition: transform 0.3s ease;
        }
        
        .chart-image:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
        
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 500;
        }
        
        .status-active {
            background: #e8f5e8;
            color: #2e7d32;
        }
        
        .status-recent {
            background: #fff8e1;
            color: #f57c00;
        }
        
        .status-stale {
            background: #ffebee;
            color: #d32f2f;
        }
        
        .battery-bar {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .battery-visual {
            width: 80px;
            height: 12px;
            background: #e9ecef;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #dee2e6;
        }
        
        .battery-fill {
            height: 100%;
            border-radius: 5px;
            transition: width 0.3s ease;
        }
        
        .battery-high { background: linear-gradient(90deg, #4CAF50, #66BB6A); }
        .battery-medium { background: linear-gradient(90deg, #FF9800, #FFB74D); }
        .battery-low { background: linear-gradient(90deg, #F44336, #EF5350); }
        
        .traceroute-section {
            margin-top: 25px;
        }
        
        .trace-path {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .hop {
            display: flex;
            align-items: center;
            padding: 12px;
            background: white;
            border-radius: 6px;
            margin-bottom: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .hop-num {
            background: linear-gradient(135deg, #2196F3, #21CBF3);
            color: white;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-weight: bold;
            font-size: 0.9em;
        }
        
        .hop-node {
            font-family: monospace;
            padding: 6px 10px;
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        
        .hop-arrow {
            margin: 0 15px;
            color: #666;
            font-size: 1.2em;
        }
        
        .hop-signal {
            margin-left: auto;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            background: #e8f5e8;
            color: #2e7d32;
            border-left: 3px solid #4CAF50;
        }
        
        .search-box {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            margin-bottom: 20px;
            transition: border-color 0.3s;
            background: white;
        }
        
        .search-box:focus {
            outline: none;
            border-color: #2196F3;
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }
        
        th {
            background: #2196F3;
            color: white;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        th:hover {
            background: #1976D2;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .empty-value {
            color: #999;
            font-style: italic;
        }
        
        .timestamp {
            font-family: monospace;
            font-size: 0.9em;
            color: #666;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .header {
                padding: 20px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .node-id-badge {
                position: static;
                margin-top: 15px;
                display: inline-block;
            }
            
            .content {
                padding: 20px;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr 1fr;
            }
            
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .hop {
                flex-wrap: wrap;
                gap: 10px;
            }
        }
        
        @media (max-width: 480px) {
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .nav-link {
                display: block;
                margin: 5px 0;
            }
        }
    """

def get_html_template(
    title: str, 
    content: str, 
    node_id: Optional[str] = None,
    navigation_links: Optional[List[Dict[str, str]]] = None,
    additional_css: str = ""
) -> str:
    """
    Generate a complete HTML page with standardized structure and styling.
    
    Args:
        title: Page title
        content: Main content HTML
        node_id: Optional node ID to display in header
        navigation_links: List of dicts with 'url' and 'text' keys
        additional_css: Additional CSS to append
    
    Returns:
        Complete HTML page as string
    """
    
    # Default navigation if none provided
    if navigation_links is None:
        navigation_links = [
            {'url': '../index.html', 'text': '🏠 Dashboard'},
            {'url': '../nodes.html', 'text': '🌐 All Nodes'},
            {'url': '../dashboards.html', 'text': '📊 Node Details'},
            {'url': '../diagnostics.html', 'text': '🔍 Diagnostics'}
        ]
    
    # Generate navigation HTML
    nav_html = ""
    if navigation_links:
        nav_links = []
        for link in navigation_links:
            nav_links.append(f'<a href="{link["url"]}" class="nav-link">{link["text"]}</a>')
        nav_html = f"""
        <div class="navigation">
            {' '.join(nav_links)}
        </div>
        """
    
    # Node ID badge if provided
    node_badge = ""
    if node_id:
        node_badge = f'<div class="node-id-badge">{node_id}</div>'
    
    # Current timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {get_standard_css()}
        {additional_css}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Generated: {timestamp}</p>
            {node_badge}
        </div>
        {nav_html}
        <div class="content">
            {content}
        </div>
    </div>
</body>
</html>"""

def format_value(value: Any, value_type: str = "text", empty_text: str = "N/A") -> str:
    """
    Format a value for display, handling empty/None values gracefully.
    
    Args:
        value: The value to format
        value_type: Type of formatting ('text', 'percent', 'voltage', 'time', 'signal')
        empty_text: Text to show for empty/None values
    
    Returns:
        Formatted string
    """
    # Handle empty values
    if value is None or value == "" or str(value).strip() == "" or str(value) in ['Unknown', 'N/A', 'null']:
        return f'<span class="empty-value">{empty_text}</span>'
    
    # Format based on type
    try:
        if value_type == "channel_util_percent" or value_type == "air_tx_percent":
            # For channel utilization and air tx, high is concerning (red)
            pct = float(value)
            if pct > 75:
                color = "#ff4d4d"  # red
            elif pct > 50:
                color = "#ffcc00"  # amber
            else:
                color = "#4CAF50"  # green
            return f'<span style="color:{color};font-weight:bold;">{pct:.1f}%</span>'
        elif value_type == "percent":
            # For battery and other percentages, low is concerning (red)
            pct = float(value)
            if pct < 25:
                color = "#ff4d4d"  # red
            elif pct < 50:
                color = "#ffcc00"  # amber
            else:
                color = "#4CAF50"  # green
            return f'<span style="color:{color};font-weight:bold;">{pct:.1f}%</span>'
        elif value_type == "voltage":
            return f"{float(value):.2f} V"
        elif value_type == "time":
            if isinstance(value, (int, float)):
                hours = float(value) / 3600
                return f"{hours:.1f} hours"
            return str(value)
        elif value_type == "signal":
            return f"{float(value):.1f} dB"
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value) if str(value) != "" else f'<span class="empty-value">{empty_text}</span>'

def create_battery_bar(battery_pct: Optional[float]) -> str:
    """
    Create a visual battery level indicator.
    
    Args:
        battery_pct: Battery percentage (0-100)
    
    Returns:
        HTML for battery bar visualization
    """
    if battery_pct is None or battery_pct == "":
        return f'<span class="empty-value">N/A</span>'
    
    try:
        pct = float(battery_pct)
        if pct > 75:
            color_class = "battery-high"
        elif pct > 25:
            color_class = "battery-medium"
        else:
            color_class = "battery-low"
        
        return f"""
        <div class="battery-bar">
            <div class="battery-visual">
                <div class="battery-fill {color_class}" style="width: {pct}%;"></div>
            </div>
            <span>{pct:.1f}%</span>
        </div>
        """
    except (ValueError, TypeError):
        return f'<span class="empty-value">Invalid</span>'

def create_status_indicator(last_seen_timestamp: Optional[str]) -> Dict[str, str]:
    """
    Create a status indicator based on last seen timestamp.
    
    Args:
        last_seen_timestamp: ISO timestamp string
    
    Returns:
        Dict with 'emoji', 'text', and 'class' keys
    """
    if not last_seen_timestamp:
        return {'emoji': '🔴', 'text': 'Unknown', 'class': 'status-stale'}
    
    try:
        from datetime import datetime, timezone
        import pandas as pd
        
        # Parse timestamp
        last_seen = pd.to_datetime(last_seen_timestamp)
        if hasattr(last_seen, 'tz') and last_seen.tz:
            current = datetime.now(timezone.utc)
        else:
            current = datetime.now()
            last_seen = last_seen.tz_localize(None) if hasattr(last_seen, 'tz_localize') else last_seen
        
        # Calculate hours since last seen
        delta = current - last_seen
        hours_ago = delta.total_seconds() / 3600
        
        if hours_ago < 1:
            return {'emoji': '🟢', 'text': 'Active', 'class': 'status-active'}
        elif hours_ago < 24:
            return {'emoji': '🟡', 'text': 'Recent', 'class': 'status-recent'}
        else:
            return {'emoji': '🔴', 'text': 'Stale', 'class': 'status-stale'}
    
    except Exception:
        return {'emoji': '🔴', 'text': 'Unknown', 'class': 'status-stale'}