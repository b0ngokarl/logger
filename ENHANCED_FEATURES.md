# Enhanced Meshtastic Telemetry Features

This document describes the new enhanced telemetry collection, automation features, and node page visualization improvements that address user requests for comprehensive telemetry data, simplified automation, and better visual representation.

## Enhanced Telemetry Collection

### Additional Sensor Data Now Collected

The enhanced telemetry system now attempts to collect data from various Meshtastic sensor types:

**Environment Sensors:**
- Temperature (°C) - from BME280, BME680, BMP280, SHT31, etc.
- Humidity (%) - from BME280, BME680, SHT31, SHT4X, etc.
- Barometric Pressure (hPa) - from BME280, BME680, BMP280, etc.
- Indoor Air Quality (IAQ) index - from BME680, etc.
- Light level (Lux) - from VEML7700, OPT3001, etc.

**Power Monitoring:**
- Device current (mA) - from INA219, INA260, etc.
- Multi-channel voltage/current monitoring - from INA3221, etc.
  - Up to 4 channels of voltage and current measurements

**Original Device Metrics (Enhanced):**
- Battery percentage - now clamped to 0-100% range to fix >100% issues
- Voltage, channel utilization, air time utilization, uptime

### How Enhanced Collection Works

1. **Multi-Sensor Queries**: For each node, the system tries multiple sensor types:
   ```
   --request-telemetry (basic device metrics)
   --request-telemetry BME280 (temperature, humidity, pressure)
   --request-telemetry BME680 (temperature, humidity, pressure, gas)
   --request-telemetry INA219 (voltage, current)
   etc.
   ```

2. **Intelligent Parsing**: Enhanced regex patterns detect and parse various sensor outputs

3. **Comprehensive Data**: All detected sensor values are stored in the CSV with dedicated columns

## One-Command Automation: `auto_meshtastic_logger.py`

### The Complete Solution

The new `auto_meshtastic_logger.py` provides the requested "one command that does everything":

```bash
# Complete automation - just run and forget
python3 auto_meshtastic_logger.py

# Everything happens automatically:
# - Node discovery
# - Telemetry collection (all sensor types)
# - Traceroute collection
# - Plot generation
# - Node completion detection
# - Timestamped output organization
```

### Key Automation Features

**Intelligent Node Management:**
- Automatic node discovery in each cycle
- Tracks when nodes are "completed" (enough data collected + timeout)
- Maintains statistics on collection progress

**Smart Scheduling:**
- Configurable collection intervals (default 5 minutes)
- Automatic plot generation at intervals or on completion
- Node completion detection based on data quantity and time

**Organized Output:**
- Creates timestamped run directories (`run_YYYYMMDD_HHMMSS`)
- Maintains `latest` symlink to current run
- Preserves history of previous runs
- JSON statistics tracking

**Completion Detection:**
- Nodes marked "complete" when:
  - Minimum telemetry count reached (default: 3 collections)
  - No new data for timeout period (default: 30 minutes)
- Automatic plotting triggered when nodes complete
- Optional stop-when-all-complete mode

### Usage Examples

**Basic Auto-Mode (Recommended):**
```bash
python3 auto_meshtastic_logger.py
```

**Custom Configuration:**
```bash
python3 auto_meshtastic_logger.py \
  --interval 300 \
  --min-telemetry-count 5 \
  --completion-timeout 1800 \
  --plot-interval 900 \
  --outdir monitoring
```

**Aggressive Monitoring:**
```bash
python3 auto_meshtastic_logger.py \
  --interval 60 \
  --plot-every-cycle \
  --stop-when-all-complete
```

### Output Structure

```
monitoring/
├── latest -> run_20250910_103045    # Symlink to current run
├── run_20250910_103045/             # Current run
│   ├── telemetry.csv               # Enhanced telemetry data
│   ├── traceroute.csv              # Traceroute data
│   ├── run_stats.json              # Collection statistics
│   └── plots/                      # Generated dashboards
│       ├── index.html              # Main dashboard
│       ├── node_exampleA/          # Per-node pages
│       │   ├── index.html          # Node dashboard
│       │   ├── battery.png         # Basic metrics
│       │   ├── voltage.png
│       │   ├── temperature.png     # NEW: Environment data
│       │   ├── humidity.png        # NEW: Environment data
│       │   └── pressure.png        # NEW: Environment data
│       └── node_exampleB/
└── run_20250910_102234/             # Previous runs preserved
```

## Enhanced Telemetry Display

### Node Dashboards Show All Data

Node pages now display all available telemetry metrics:

**Always Present:**
- Battery, Voltage, Channel Utilization, Air TX, Uptime

**When Available (NEW):**
- Temperature (°C)
- Humidity (%)
- Barometric Pressure (hPa)  
- Air Quality Index (IAQ)
- Light Level (Lux)
- Current (mA)
- Multi-channel voltage/current

### Fixed Battery Calculation

- Battery percentages now clamped to 0-100% range
- Improved runtime estimation algorithm
- More accurate "Est. runtime" calculations

## Migration Guide

### For Simple Use Cases

**Old Way:**
```bash
# Multiple manual steps required
python3 discover_nodes_refactored.py
python3 meshtastic_logger_refactored.py --all-nodes --once --plot
# Repeat manually...
```

**New Way:**
```bash
# Single command does everything
python3 auto_meshtastic_logger.py
```

### For Advanced Use Cases

The original scripts still work unchanged, but now collect enhanced telemetry:

```bash
# Enhanced telemetry with original workflow
python3 meshtastic_logger_refactored.py --all-nodes --once --plot
python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv
```

### CSV Format Changes

**Enhanced telemetry CSV now includes:**
```csv
timestamp,node,battery_pct,voltage_v,channel_util_pct,air_tx_pct,uptime_s,temperature_c,humidity_pct,pressure_hpa,iaq,lux,current_ma,ch1_voltage_v,ch1_current_ma,ch2_voltage_v,ch2_current_ma,ch3_voltage_v,ch3_current_ma,ch4_voltage_v,ch4_current_ma
```

**Backward Compatibility:**
- Old CSV files still work with plotting
- New columns are optional (empty if sensor not present)
- All existing functionality preserved

## Benefits

1. **Complete Telemetry**: Collects all available sensor data, not just basic device metrics
2. **True Automation**: Single command handles entire workflow with intelligent scheduling
3. **Better Data Quality**: Fixed battery calculation issues and improved parsing
4. **Organized Output**: Timestamped runs with preserved history
5. **Completion Detection**: Knows when nodes are "done" and acts accordingly
6. **Flexible Deployment**: Works from simple one-shot to complex monitoring scenarios

## Troubleshooting

**No Additional Sensors Detected:**
- Normal if nodes don't have environment/power sensors
- Basic device metrics (battery, voltage, etc.) still collected
- Check hardware documentation for supported sensors

**Large CSV Files:**
- Additional columns may increase file size
- Empty columns for unsupported sensors are minimal overhead
- Use `--no-trace` to reduce traceroute data if needed

**Automation Not Stopping:**
- Check `--completion-timeout` setting
- Use `--stop-when-all-complete` for finite runs
- Monitor via `run_stats.json` for progress tracking

## Node Page Visualization Enhancements

The node pages have been enhanced with improved visualizations and fixes:

### Fixed Duplicate Node ID Display

- Removed redundant Node ID from node information tables
- Node ID now appears only in the page header and badge
- Implementation: `node_page_updater.py --fix-duplicate-node-id`

### Enhanced Battery Visualization

- Added visual battery progress bars with color coding:
  - Green (>75%): Good battery level
  - Yellow (40-75%): Medium battery level
  - Orange (20-40%): Low battery level
  - Red (<20%): Critical battery level
- Implementation: `enhance_node_visualizations.py`

### Color-Coded Metrics

- Added color indicators to important metrics:
  - Channel Utilization: Green (<10%), Yellow (<25%), Orange (<50%), Red (>50%)
  - Air TX: Green (<5%), Yellow (<15%), Orange (<30%), Red (>30%)
- Implementation: `enhance_node_visualizations.py`

### Example Node Enhancements

- Added realistic battery metrics to example nodes
- Different battery levels for demonstration: 95%, 75%, 35%, 15%
- Implementation: `add_battery_to_examples.py`

### Pipeline Integration

- Updated `pipeline.py` to include all enhancement steps
- Single command to run all fixes: `python3 pipeline.py --skip-plot`

### Usage Examples

```bash
# Fix duplicate Node ID display
python3 node_page_updater.py --fix-duplicate-node-id

# Enhance metrics visualization
python3 enhance_node_visualizations.py plots

# Add battery metrics to example nodes
python3 add_battery_to_examples.py

# Run complete pipeline (skip plot generation)
python3 pipeline.py --skip-plot

# Run validation tests
python3 validate_enhancements.py
```