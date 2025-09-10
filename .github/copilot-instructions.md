# Meshtastic Telemetry & Traceroute Logger

A Python toolkit for collecting, logging, and visualizing telemetry and traceroute data from Meshtastic nodes with a modular architecture.

**ALWAYS reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap Environment
- Install Python 3.10+ (Python 3.12.3 tested and working):
  ```bash
  python3 --version  # Verify 3.10+
  ```
- Install dependencies (takes 2-3 minutes, NEVER CANCEL):
  ```bash
  cd /home/runner/work/logger/logger
  pip install -r requirements.txt
  ```

### Run Tests and Validation
- **ALWAYS** run unit tests first (takes <1 second):
  ```bash
  python3 -m unittest tests.test_core_modules -v
  ```
- Validate plotting functionality with sample data (takes ~3 seconds):
  ```bash
  python3 plot_meshtastic.py --telemetry examples/telemetry_example.csv --traceroute examples/traceroute_example.csv --outdir /tmp/test_plots
  ```
- **MANUAL VALIDATION REQUIREMENT**: After running plotting, verify the HTML dashboard works:
  ```bash
  ls -la /tmp/test_plots/  # Should show index.html, PNG files, node directories
  ```

### Core Scripts Usage
- **Primary script** (use this, not legacy files):
  ```bash
  python3 meshtastic_logger_refactored.py --help
  python3 meshtastic_logger_refactored.py --all-nodes --once --plot
  ```
- **Node discovery**:
  ```bash
  python3 discover_nodes_refactored.py --detailed
  ```
- **Plot generation only**:
  ```bash
  python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --outdir plots
  ```
- **Node page enhancement**:
  ```bash
  # Fix all issues at once
  python3 node_page_updater.py --fix-all
  
  # Fix only duplicate Node ID issue
  python3 node_page_updater.py --fix-duplicate-node-id
  
  # Enhance metrics visualization
  python3 node_page_updater.py --enhance-metrics
  
  # Run complete pipeline
  python3 pipeline.py --skip-plot
  ```

### Expected Hardware Requirements
- **WITHOUT Meshtastic Hardware**: Scripts run but show "No nodes discovered" - this is normal for testing
- **WITH Meshtastic Hardware**: Requires serial device (e.g., /dev/ttyACM0) for actual data collection
- **Sample Data Available**: Use files in `examples/` directory for development and testing

## Validation Scenarios

### After Making Changes - ALWAYS Run These:
1. **Unit Test Validation** (~1 second):
   ```bash
   python3 -m unittest tests.test_core_modules -v
   ```
2. **Plot Generation Test** (~3 seconds):
   ```bash
   python3 plot_meshtastic.py --telemetry examples/telemetry_example.csv --traceroute examples/traceroute_example.csv --outdir /tmp/validation_plots
   ```
3. **Script Help Validation** (immediate):
   ```bash
   python3 meshtastic_logger_refactored.py --help
   python3 discover_nodes_refactored.py --help
   ```
4. **Manual Output Verification**: Always check that `/tmp/validation_plots/index.html` exists and contains expected dashboard content

### End-to-End Scenario Testing
- **Test Complete Workflow**: Generate plots from sample data, verify HTML dashboard loads, check PNG files created
- **Test Node Discovery**: Run discovery script (expects "No nodes discovered" without hardware)
- **Test Main Logger**: Run with `--once` flag (expects warning about no nodes without hardware)

## Build and Deploy

### No Build Process Required
- Pure Python application - no compilation needed
- Dependencies install via pip only
- No Makefile, configure scripts, or build systems

### Code Quality
- Linting configuration exists in `.trunk/trunk.yaml` but requires trunk CLI installation
- No automated formatting tools available in standard environment
- Manual code review recommended

## Architecture and Navigation

### Key Directories
- **`core/`**: Modular utility functions (cli_utils, csv_utils, node_discovery, telemetry, traceroute)
- **`tests/`**: Unit tests for core modules
- **`examples/`**: Sample CSV data for development and testing
- **`sample_output/`**: Example output structure
- **Root**: Main executable scripts

### Important Files
- **`meshtastic_logger_refactored.py`**: RECOMMENDED main logging script (clean, modular)
- **`discover_nodes_refactored.py`**: RECOMMENDED node discovery script
- **`plot_meshtastic.py`**: Plot and dashboard generation
- **`node_page_updater.py`**: Script to fix and enhance node pages
- **`enhance_node_visualizations.py`**: Enhances metrics with colors and progress bars
- **`add_battery_to_examples.py`**: Adds realistic metrics to example nodes
- **`pipeline.py`**: End-to-end script that runs all necessary steps
- **`meshtastic_telemetry_logger.py`**: LEGACY monolithic script (avoid for new work)

### File Dependencies
- Main scripts import from `core/` modules
- Always check `core/` modules when modifying validation logic
- CSV utilities in `core/csv_utils.py` handle all data logging
- HTML generation in `core/html_templates.py`

## Common Tasks

### Repository Structure
```
.
├── README.md                          # Main documentation
├── REFACTORING_GUIDE.md              # Migration guide
├── requirements.txt                   # Python dependencies
├── core/                             # Modular utility functions
│   ├── cli_utils.py                 # Command validation
│   ├── csv_utils.py                 # Data logging
│   ├── node_discovery.py            # Network discovery
│   ├── telemetry.py                 # Data collection
│   └── traceroute.py                # Network topology
├── tests/
│   └── test_core_modules.py         # Unit tests (7 tests, <1s)
├── examples/
│   ├── telemetry_example.csv        # Sample telemetry data
│   └── traceroute_example.csv       # Sample traceroute data
├── meshtastic_logger_refactored.py  # Main script (RECOMMENDED)
├── discover_nodes_refactored.py     # Discovery script (RECOMMENDED)
├── plot_meshtastic.py               # Plotting and HTML generation
├── node_page_updater.py             # Node page enhancement script
├── enhance_node_visualizations.py   # Visualization enhancement script
├── add_battery_to_examples.py       # Example node enhancement script
├── pipeline.py                      # End-to-end pipeline script
└── meshtastic_telemetry_logger.py   # Legacy script (AVOID)
```

### Sample Commands Output
```bash
# Unit tests
$ python3 -m unittest tests.test_core_modules -v
# Runs 7 tests in 0.002s, all should pass

# Plot generation
$ python3 plot_meshtastic.py --telemetry examples/telemetry_example.csv --traceroute examples/traceroute_example.csv --outdir /tmp/plots
# Creates HTML dashboard with PNG charts, takes ~2-3 seconds

# Script without hardware
$ python3 meshtastic_logger_refactored.py --all-nodes --once
# Shows "No target nodes found" - normal without Meshtastic devices
```

## Timing Expectations

- **Unit Tests**: <0.1 seconds (7 tests) - NEVER CANCEL, set timeout to 30+ seconds
- **Dependency Installation**: 2-5 minutes on fresh install - NEVER CANCEL, set timeout to 300+ seconds
- **Plot Generation**: ~2.4 seconds with sample data - NEVER CANCEL, set timeout to 30+ seconds
- **Script Execution**: Immediate response (<1 second) when no hardware present
- **Manual Validation**: Always verify generated HTML files open correctly and contain expected dashboard content

## Troubleshooting

### Common Issues
- **"No nodes discovered"**: Normal without Meshtastic hardware connected
- **Import errors**: Run `pip install -r requirements.txt` first
- **Missing output files**: Check that output directory exists and has write permissions
- **HTML dashboard not loading**: Verify PNG files were generated alongside HTML files
- **Duplicate Node ID in pages**: Run `python3 node_page_updater.py --fix-duplicate-node-id` to fix
- **Missing battery visualization**: Run `python3 add_battery_to_examples.py` to add battery metrics to example nodes
- **Plain metrics without colors**: Run `python3 enhance_node_visualizations.py plots` to enhance with colors

### Always Test With Sample Data First
- Use `examples/telemetry_example.csv` and `examples/traceroute_example.csv` for development
- Generate plots to `/tmp/test_plots/` to avoid cluttering repository
- Verify `index.html` opens and shows dashboard with charts before testing with real hardware

### Hardware-Specific Notes
- Scripts expect Meshtastic devices on serial ports (e.g., /dev/ttyACM0)
- Without hardware: scripts run but collect no data (this is expected)
- With hardware: actual telemetry and traceroute data will be collected and logged to CSV files