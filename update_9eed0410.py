#!/usr/bin/env python3
"""
Script to directly update node 9eed0410 with telemetry data
"""
from node_page_updater import NodePageUpdater

def fix_status_indicator(html_path):
    """Fix the status indicator in the HTML file and add Last Heard information"""
    with open(html_path, 'r') as file:
        content = file.read()
    
    # Replace the status indicator
    content = content.replace(
        '<span class="status-indicator status-stale">🔴 Unknown</span>',
        '<span class="status-indicator status-online">🟢 Online</span>'
    )
    
    # Add Last Heard information
    last_heard_row = '''
        <tr>
            <td><strong>Last Heard</strong></td>
            <td>2025-09-10 19:45:28 UTC</td>
        </tr>
    '''
    
    # Find the end of the Node ID row and insert the Last Heard row after it
    node_id_end = content.find('</tr>', content.find('<td>!9eed0410</td>'))
    if node_id_end > 0:
        content = content[:node_id_end+5] + last_heard_row + content[node_id_end+5:]
    
    with open(html_path, 'w') as file:
        file.write(content)
    
    return True

def main():
    updater = NodePageUpdater(output_dir="plots")
    
    # Create telemetry data from the real telemetry.csv entry
    telemetry_data = {
        "timestamp": "2025-09-10T19:45:28",
        "battery_pct": 79.0,
        "voltage_v": 3.98,
        "channel_util_pct": 32.07,
        "air_tx_pct": 1.77,
        "uptime_s": 13383.0,
        "status": "online",
        "last_heard": "2025-09-10T19:45:28"  # Using the timestamp as last_heard
    }
    
    # Update the node page
    result = updater.update_node_page("!9eed0410", telemetry_data)
    if result:
        print(f"Successfully updated node page: {result}")
    else:
        print("Failed to update node page")
    
    # Apply fixes and enhancements
    updater.fix_duplicate_node_id()
    updater.enhance_metrics_visualization()
    
    # Update the page again to ensure all fixes are applied
    html_path = updater.update_node_page("!9eed0410", telemetry_data)
    
    # Fix the status indicator
    if html_path and fix_status_indicator(html_path):
        print(f"Fixed status indicator in {html_path}")
    
    print("Done")

if __name__ == "__main__":
    main()
