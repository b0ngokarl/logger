# Meshtastic Telemetry & Traceroute Logger

A toolkit for collecting, logging, and visualizing telemetry and traceroute data from Meshtastic nodes.

## Features

- Collects telemetry (battery, voltage, channel utilization, air time, uptime) from Meshtastic nodes
- Captures traceroute data between nodes to understand the mesh topology
- Logs data to CSV files with timestamps
- Generates interactive HTML dashboards with visualizations
- Creates per-node dedicated pages with detailed metrics and traceroute information

## Files

- `meshtastic_telemetry_logger.py`: Main script for collecting and logging data
- `discover_all_nodes.py`: Script for automatically discovering all nodes on the network
- `node_page_updater.py`: Class for updating node-specific pages
- `update_node_pages.py`: Helper script for generating per-node HTML dashboards
- `test_node_pages.py`: Test utility for the node pages generator
- `test_all_nodes.py`: Example script demonstrating all-nodes discovery and chart regeneration
- `plots/`: Directory containing generated visualizations and HTML dashboards
  - `index.html`: Main dashboard entry point
  - `dashboards.html`: Grid of all node dashboards with key metrics
  - `nodes.html`: Table of all discovered nodes
  - `diagnostics.html`: Detailed diagnostic information
  - `node_{id}/`: Per-node directories containing dedicated dashboards
    - `index.html`: Node-specific dashboard with telemetry and traceroute data
    - Various metric graphs (PNG files)

## Recent Changes

- Added automatic node discovery with the `--all-nodes` flag
- Added chart regeneration option with the `--regenerate-charts` flag
- Added per-node dedicated pages with both telemetry and traceroute data
- Improved traceroute visualization with better styling and layout
- Created a dashboard grid for easy navigation between nodes
- Enhanced integration between telemetry and traceroute data
- Added directional path visualization (forward/backward paths)

## Usage Examples

### Discover All Nodes Automatically

```bash
python3 meshtastic_telemetry_logger.py --all-nodes --once
```

### Force Chart Regeneration

```bash
python3 meshtastic_telemetry_logger.py --nodes !exampleA --once --regenerate-charts
```

### Run Plot Generation with Chart Regeneration

```bash
python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --regenerate-charts
```
