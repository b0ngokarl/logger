#!/usr/bin/env python3
"""
This is a manual update script for the dashboard.html to use our new grid layout.
"""
from pathlib import Path
import time

def update_dashboard():
    print("Updating dashboards.html with new grid layout...")
    plot_dir = Path("plots")
    
    # Find all node directories, excluding example nodes
    node_dirs = [d for d in plot_dir.glob("node_*") if d.is_dir() and not d.name.startswith("node_example")]
    print(f"Found {len(node_dirs)} non-example node directories")
    
    # Create dashboards HTML with grid layout
    dashboards_html = """<!doctype html>
<meta charset='utf-8'>
<title>Node Dashboards</title>
<style>
body {font-family: Arial, sans-serif; margin: 20px;}
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-top: 20px;
}
.node-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
}
.node-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.15);
}
.node-id {
    font-family: monospace;
    background-color: #f5f5f5;
    padding: 3px 6px;
    border-radius: 3px;
    font-size: 14px;
    margin-left: 8px;
}
.view-btn {
    display: inline-block;
    background-color: #4CAF50;
    color: white;
    padding: 8px 16px;
    border-radius: 4px;
    margin-top: 15px;
    text-decoration: none;
    text-align: center;
}
.view-btn:hover {
    background-color: #45a049;
}
h1 {margin-bottom: 10px;}
</style>
<h1>Node Dashboards</h1>
<p>Last updated: """
    
    # Add current time
    dashboards_html += time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    dashboards_html += f" - {len(node_dirs)} nodes</p>"
    dashboards_html += """<p><a href="index.html">Back to index</a></p>

<div class="dashboard-grid">
"""
    
    # Add a card for each node
    for node_dir in node_dirs:
        # Skip example nodes
        if node_dir.name.startswith("node_example"):
            continue
            
        node_id = "!" + node_dir.name.replace("node_", "")
        
        # Try to read some basic info from the node's data file if it exists
        node_title = "Node"
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
        except Exception:
            pass
            
        dashboards_html += f"""
<div class="node-card">
    <h3>{node_title} <span class="node-id">{node_id}</span></h3>
    <a href="{node_dir.name}/index.html" class="view-btn">View Details</a>
</div>
"""
    
    dashboards_html += """
</div>
</html>
"""
    
    # Write the dashboard HTML
    dashboard_path = plot_dir / "dashboards.html"
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(dashboards_html)
    
    print(f"Updated dashboards.html at {dashboard_path}")

if __name__ == "__main__":
    update_dashboard()
