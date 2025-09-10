# Meshtastic Telemetry & Traceroute Logger

A toolkit for collecting, logging, and visualizing telemetry and traceroute data from Meshtastic nodes.

## ⚡ New Refactored Version Available!

This repository has been refactored for better maintainability and modularity. See [`REFACTORING_GUIDE.md`](REFACTORING_GUIDE.md) for migration details.

**Quick Start with Refactored Version:**
```bash
# Auto-discover and monitor all nodes
python3 meshtastic_logger_refactored.py --all-nodes --once --plot

# Monitor specific nodes  
python3 meshtastic_logger_refactored.py --nodes !abc123 !def456 --once --plot

# Discover nodes only
python3 discover_nodes_refactored.py --detailed
```

## Features

- Collects telemetry (battery, voltage, channel utilization, air time, uptime) from Meshtastic nodes
- Captures traceroute data between nodes to understand the mesh topology
- Logs data to CSV files with timestamps
- Generates interactive HTML dashboards with visualizations
- Creates per-node dedicated pages with detailed metrics and traceroute information
- **NEW**: Modular architecture with core utility modules
- **NEW**: Comprehensive unit testing
- **NEW**: Configuration management system

## Architecture

### Core Modules (`core/`)
- **`cli_utils.py`**: Safe CLI command execution and validation
- **`csv_utils.py`**: CSV file handling and data logging utilities  
- **`node_discovery.py`**: Network node discovery and detailed node information
- **`telemetry.py`**: Telemetry data collection from Meshtastic nodes
- **`traceroute.py`**: Network traceroute functionality and topology analysis
- **`config.py`**: Configuration management system

### Main Scripts
- **`meshtastic_logger_refactored.py`**: Clean, class-based main logger (recommended)
- **`discover_nodes_refactored.py`**: Simplified node discovery script
- **`meshtastic_telemetry_logger.py`**: Original monolithic implementation (legacy)

## Files

- `meshtastic_telemetry_logger.py`: Legacy main script for collecting and logging data
- `meshtastic_logger_refactored.py`: **Recommended** refactored main logger with modular architecture
- `discover_nodes_refactored.py`: Node discovery script using core modules  
- `node_page_updater.py`: Class for updating node-specific pages
- `update_node_pages.py`: Helper script for generating per-node HTML dashboards
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

### Quick Start (Refactored Version)

**Discover All Nodes Automatically:**
```bash
python3 meshtastic_logger_refactored.py --all-nodes --once --plot
```

**Monitor Specific Nodes:**
```bash
python3 meshtastic_logger_refactored.py --nodes !abc123 !def456 --once --plot
```

**Continuous Monitoring:**
```bash
python3 meshtastic_logger_refactored.py --all-nodes --interval 300 --plot
```

**Node Discovery Only:**
```bash
python3 discover_nodes_refactored.py --detailed
```

### Legacy Usage (Original Files)

**Discover All Nodes Automatically:**

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
