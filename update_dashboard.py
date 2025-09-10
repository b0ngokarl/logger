#!/usr/bin/env python3
"""
This is a manual update script for the dashboard.html to use our new grid layout.
Updated to use standardized HTML templates for consistent styling.
"""
from pathlib import Path
import time
import sys
import os

# Add core module to path for template imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))
try:
    from html_templates import get_html_template, format_value, create_battery_bar, create_status_indicator
except ImportError:
    print("[WARN] Could not import html_templates, using basic styling", file=sys.stderr)

def update_dashboard():
    print("Updating dashboards.html with new grid layout...")
    plot_dir = Path("plots")
    
    # Find all node directories, excluding example nodes
    node_dirs = [d for d in plot_dir.glob("node_*") if d.is_dir() and not d.name.startswith("node_example")]
    print(f"Found {len(node_dirs)} non-example node directories")
    
    # Build the content using standardized template
    content = _build_dashboard_content(node_dirs)
    
    # Navigation links
    navigation = [
        {'url': 'index.html', 'text': '🏠 Main Dashboard'},
        {'url': 'nodes.html', 'text': '🌐 All Nodes'}, 
        {'url': 'diagnostics.html', 'text': '🔍 Diagnostics'}
    ]
    
    # Use standardized HTML template if available
    try:
        html_content = get_html_template(
            title="📊 Node Dashboards",
            content=content,
            navigation_links=navigation
        )
    except NameError:
        # Fallback if template import failed
        html_content = _fallback_dashboard_html(node_dirs)
    
    # Write the dashboard HTML
    dashboard_path = plot_dir / "dashboards.html"
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Updated dashboards.html at {dashboard_path}")

def _build_dashboard_content(node_dirs):
    """Build the main dashboard content with node cards."""
    if not node_dirs:
        return """
        <div class="section">
            <h2>📊 Node Dashboards</h2>
            <p><em>No node directories found. Generate some telemetry data first using the logger scripts.</em></p>
        </div>
        """
    
    # Build node cards
    node_cards = []
    for node_dir in sorted(node_dirs):
        node_id = "!" + node_dir.name.replace("node_", "")
        
        # Try to read some basic info from the node's data file if it exists
        node_title = "Node"
        node_info = ""
        try:
            index_path = node_dir / "index.html"
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Try to extract title or user info if available
                    import re
                    title_match = re.search(r'<h3>([^<]+)<span', content)
                    if title_match:
                        node_title = title_match.group(1).strip()
                    
                    # Try to extract some basic info
                    info_matches = re.findall(r'<td[^>]*><strong>([^<]+)</strong></td>\s*<td[^>]*>([^<]+)</td>', content)
                    if info_matches:
                        # Show first few info items
                        info_items = []
                        for field, value in info_matches[:3]:
                            if field not in ['Node ID'] and value != 'N/A':
                                info_items.append(f"{field}: {value}")
                        if info_items:
                            node_info = " • ".join(info_items)
        except Exception as e:
            print(f"[DEBUG] Could not extract info for {node_id}: {e}")
        
        node_cards.append(f"""
        <div class="metric-card" style="min-height: 120px;">
            <h3 style="margin-top: 0; color: #2196F3;">{node_title}</h3>
            <div style="font-family: monospace; background: #f8f9fa; padding: 4px 8px; border-radius: 4px; margin: 10px 0; display: inline-block;">
                {node_id}
            </div>
            {f'<p style="font-size: 0.9em; color: #666; margin: 8px 0;">{node_info}</p>' if node_info else ''}
            <div style="margin-top: auto;">
                <a href="{node_dir.name}/index.html" class="nav-link" style="display: inline-block; margin: 0; padding: 8px 16px; font-size: 0.9em;">
                    📈 View Details
                </a>
            </div>
        </div>
        """)
    
    return f"""
    <div class="section">
        <h2>📊 Node Dashboards</h2>
        <p>Individual node dashboards with telemetry data, charts, and routing information.</p>
        
        <div style="text-align: center; margin: 20px 0; padding: 15px; background: #e3f2fd; border-radius: 8px;">
            <strong>{len(node_dirs)} nodes</strong> with dashboard data available
        </div>
        
        <div class="metrics-grid">
            {''.join(node_cards)}
        </div>
    </div>
    """

def _fallback_dashboard_html(node_dirs):
    """Fallback HTML if the standardized template import fails."""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    
    cards_html = ""
    for node_dir in sorted(node_dirs):
        node_id = "!" + node_dir.name.replace("node_", "")
        node_title = "Node"
        
        try:
            index_path = node_dir / "index.html"
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    import re
                    title_match = re.search(r'<h3>([^<]+)<span', content)
                    if title_match:
                        node_title = title_match.group(1).strip()
        except Exception:
            pass
        
        cards_html += f"""
        <div class="node-card">
            <h3>{node_title} <span class="node-id">{node_id}</span></h3>
            <a href="{node_dir.name}/index.html" class="view-btn">View Details</a>
        </div>
        """
    
    return f"""<!doctype html>
<meta charset='utf-8'>
<title>Node Dashboards</title>
<style>
body {{font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5;}}
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
    background: white;
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
</style>
<h1>Node Dashboards</h1>
<p>Last updated: {timestamp} - {len(node_dirs)} nodes</p>
<p><a href="index.html">Back to index</a></p>

<div class="dashboard-grid">
{cards_html}
</div>
</html>"""

if __name__ == "__main__":
    update_dashboard()
