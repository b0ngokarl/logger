# Add this code to regenerate plots and create pages for all discovered nodes

def add_regenerate_plots_and_all_nodes_pages():
    """
    This function adds functionality to regenerate all plots and create pages for all discovered nodes
    """
    # Create a text file with instructions
    instruction_text = """
To add the ability to regenerate all charts and create pages for all discovered nodes, 
follow these steps:

1. Modify plot_meshtastic.py to accept a --regenerate-charts flag:
   - Add the flag to the argparse.ArgumentParser in parse_args() function
   - Add logic to force regeneration of all charts when the flag is present

2. Modify meshtastic_telemetry_logger.py to:
   - Get all discovered nodes from meshtastic --nodes command
   - Pass the --regenerate-charts flag to plot_meshtastic.py
   - Create pages for all discovered nodes, not just those with traceroute data

Here are the necessary code changes:

Step 1: Modify plot_meshtastic.py
Add to parse_args() function:
```python
ap.add_argument("--regenerate-charts", action="store_true", help="Force regeneration of all charts")
```

Step 2: Modify meshtastic_telemetry_logger.py main() function:
Add before auto-plotting:
```python
# Create pages for all nodes found via meshtastic --nodes
print("[INFO] Getting list of all discovered nodes...")
success, nodes_output = run_cli(["meshtastic", "--nodes"])
all_discovered_nodes = []
if success:
    # Parse the nodes output to extract all node IDs
    lines = nodes_output.splitlines()
    for line in lines:
        if "!" in line and "│" in line:
            parts = line.split("│")
            if len(parts) >= 3:  # Node ID is typically in the 3rd column
                node_id = parts[2].strip()
                if node_id.startswith("!") and len(node_id) > 1:
                    all_discovered_nodes.append(node_id)
    
    print(f"[INFO] Found {len(all_discovered_nodes)} nodes from meshtastic --nodes")
```

Add to plot command:
```python
plot_cmd = [
    "python3", "plot_meshtastic.py", 
    "--telemetry", args.output, 
    "--traceroute", args.trace_output, 
    "--outdir", args.plot_outdir
]
if args.regenerate_charts:
    plot_cmd.append("--regenerate-charts")
subprocess.run(plot_cmd, check=False)
```

Add after processing nodes with traceroute data:
```python
# Now, create pages for all discovered nodes (if they don't already have a page)
if all_discovered_nodes:
    processed_nodes = set(traceroutes.keys())  # We already processed these
    
    for node_id in all_discovered_nodes:
        # Skip if this node already has a page from traceroute data
        if node_id in processed_nodes:
            continue
            
        # Load historical telemetry data for this node
        node_telemetry = {}
        normalized_node_id = node_id.strip('!')
        
        if Path("telemetry_log.csv").exists():
            try:
                # Use grep to find matching lines for this node
                grep_result = subprocess.run(
                    ["grep", normalized_node_id, "telemetry_log.csv"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if grep_result.stdout:
                    matching_lines = grep_result.stdout.strip().split('\n')
                    metrics = ["battery_pct", "voltage_v", "channel_util_pct", "air_tx_pct", "uptime_s"]
                    
                    # Process lines from most recent backward
                    for line in reversed(matching_lines):
                        parts = line.split(",")
                        if len(parts) >= 7:
                            for i, metric in enumerate(metrics):
                                # Only set if we haven't found this metric yet
                                if metric not in node_telemetry and parts[i+2].strip():
                                    try:
                                        node_telemetry[metric] = float(parts[i+2])
                                    except ValueError:
                                        pass
            except Exception as e:
                print(f"[WARN] Error loading historical data for {node_id}: {e}", file=sys.stderr)
                
        # Create/update page for this node
        if node_telemetry:
            print(f"[INFO] Creating page for discovered node {node_id} with historical data")
        else:
            print(f"[INFO] Creating empty page for discovered node {node_id}")
            
        update_node_pages_module.update_node_pages(node_id, node_telemetry, None, args.plot_outdir)
    
    print(f"[INFO] Created pages for {len(all_discovered_nodes) - len(processed_nodes)} additional discovered nodes")
```

Step 3: Add a regenerate-charts argument to meshtastic_telemetry_logger.py
Add to parse_arguments() function:
```python
p.add_argument("--regenerate-charts", action="store_true", help="Force regeneration of all node charts")
```
"""
    
    return instruction_text
