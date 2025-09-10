# Unified Meshtastic Logger - Alpha Version

## Overview

The **Unified Meshtastic Logger** is a comprehensive, single-script solution that consolidates all Meshtastic telemetry and traceroute functionality into one seamless interface. This alpha version features enhanced organization, improved maintainability, and modernized code structure while preserving all existing functionality.

## 🚀 Key Features

### Unified Interface
- **Single Command**: All functionality accessible through one script with alpha-grade reliability
- **Integrated Plotting**: Automatic dashboard generation with enhanced Python interpreter detection
- **Smart Discovery**: Intelligent node discovery and management with improved error handling
- **Comprehensive Logging**: Telemetry and traceroute data collection in one optimized workflow

### Enhanced Functionality  
- **Real-time Monitoring**: Continuous data collection with configurable intervals and improved stability
- **Dashboard Generation**: Automatic HTML dashboard creation with modern responsive design
- **Error Recovery**: Robust error handling and graceful degradation with alpha-level resilience
- **Statistics Tracking**: Comprehensive statistics and final summaries with enhanced metrics

### Flexible Usage Modes
- **Discovery Mode**: `--discover` - Find and display available nodes
- **One-shot Collection**: `--once` - Single data collection cycle
- **Continuous Monitoring**: `--interval` - Automated recurring collection
- **Plot-only Mode**: Use existing data to generate fresh dashboards

## 📋 Quick Start

### Basic Usage Examples

```bash
# Discover available nodes
./meshtastic_unified.py --discover

# Monitor specific nodes once with dashboard
./meshtastic_unified.py --nodes !abc123 !def456 --once --plot

# Monitor all nodes continuously with auto-plotting
./meshtastic_unified.py --all-nodes --auto-plot --interval 300

# Collect data without plotting (faster)
./meshtastic_unified.py --nodes !abc123 --once --no-plot

# Force regenerate all charts
./meshtastic_unified.py --all-nodes --once --plot --regenerate-charts
```

### Advanced Usage

```bash
# Continuous monitoring with custom output location
./meshtastic_unified.py --all-nodes --auto-plot --interval 600 \\
    --output data/telemetry.csv --trace-output data/traceroute.csv \\
    --plot-outdir dashboards

# Telemetry-only collection (no traceroute)
./meshtastic_unified.py --nodes !abc123 --no-trace --once --plot

# Verbose debugging mode
./meshtastic_unified.py --discover --verbose

# Custom serial device and timeout
./meshtastic_unified.py --all-nodes --once --plot \\
    --serial /dev/ttyACM0 --timeout 45
```

## 🔧 Command Line Options

### Node Selection (Required - Choose One)
- `--nodes NODE_ID [NODE_ID ...]`: Monitor specific nodes (e.g., `!abc123 !def456`)
- `--all-nodes`: Auto-discover and monitor all available nodes
- `--discover`: Discover and display available nodes, then exit

### Connection Options
- `--serial DEVICE`: Serial device path (e.g., `/dev/ttyACM0`, auto-detected if not specified)
- `--timeout SECONDS`: Timeout for Meshtastic operations (default: 30)

### Output Options
- `--output FILE`: Telemetry CSV output file (default: `telemetry.csv`)
- `--trace-output FILE`: Traceroute CSV output file (default: `traceroute.csv`)
- `--plot-outdir DIR`: Output directory for plots and HTML dashboard (default: `plots`)

### Execution Modes
- `--once`: Run one collection cycle and exit
- `--interval SECONDS`: Interval between cycles in seconds (default: 300)

### Feature Controls
- `--no-trace`: Disable traceroute collection (faster, telemetry only)
- `--plot`: Generate plots and dashboard after data collection
- `--auto-plot`: Automatically generate plots after each cycle
- `--no-plot`: Disable all plotting (data collection only)

### Advanced Options
- `--regenerate-charts`: Force regeneration of all charts
- `--preserve-history`: Create timestamped directories and preserve plot history
- `--verbose`: Enable verbose output for debugging

## 📊 Output Files and Dashboard

### Generated Files
```
plots/
├── index.html              # Main dashboard entry point
├── diagnostics.html        # Data quality and merge verification
├── nodes.html             # Complete network directory
├── dashboards.html        # Grid of all node dashboards
├── node_[id]/            # Per-node directories
│   ├── index.html        # Node-specific dashboard
│   └── *.png            # Individual metric charts
├── traceroute_*.png      # Network analysis charts
├── topology_*.png        # Network topology snapshots
└── nodes_data.json       # Node tracking data
```

### CSV Data Files
```
telemetry.csv             # Time-series telemetry data
traceroute.csv           # Network topology and routing data
```

## 🔍 Key Improvements in Beta

### Unified Workflow
- **No More Manual Steps**: Single command handles everything
- **Proper Python Detection**: Uses the same interpreter for all operations
- **Integrated Error Handling**: Comprehensive error recovery and reporting

### Enhanced User Experience
- **Rich Output**: Unicode icons, colored output, progress indicators
- **Clear Statistics**: Final summaries with comprehensive metrics
- **Better Documentation**: Inline help and detailed examples

### Robust Operation
- **Graceful Degradation**: Continues operation despite individual failures
- **Signal Handling**: Proper cleanup on interruption
- **Resource Management**: Efficient memory and file handling

### Corrected Issues
- **Fixed Plotting Integration**: No more pandas import errors
- **Improved Node Discovery**: Better handling of unavailable nodes
- **Consistent File Paths**: Proper absolute path handling throughout
- **Dashboard Generation**: Reliable HTML output with all navigation links

## 🧪 Testing and Validation

### Run the Test Suite
```bash
# Run comprehensive tests
python3 test_unified_alpha.py

# Test with sample data
python3 meshtastic_unified.py --nodes !2c9e092b --once --plot
```

### Expected Behavior
- **With Hardware**: Full data collection and dashboard generation
- **Without Hardware**: Graceful handling, sample dashboard creation
- **Error Conditions**: Clear error messages and recovery

## 🔄 Migration from Multiple Scripts

### Before (Multiple Commands)
```bash
# Old workflow required multiple steps
python3 meshtastic_logger_refactored.py --nodes !abc123 --once
python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --outdir plots
```

### After (Single Command)
```bash
# New unified workflow
./meshtastic_unified.py --nodes !abc123 --once --plot
```

### Compatibility
- All existing CSV data formats are supported
- Existing plot configurations are preserved
- Core module functionality remains unchanged
- All HTML templates and styling are maintained

## 📈 Performance and Reliability

### Optimizations
- **Efficient Data Collection**: Batched operations reduce overhead
- **Smart Plotting**: Only regenerates when necessary
- **Resource Cleanup**: Proper file and memory management
- **Interrupt Handling**: Clean shutdown on CTRL+C

### Error Resilience
- **Connection Failures**: Graceful handling of serial connection issues
- **Partial Data**: Continues operation with incomplete data sets
- **File Errors**: Robust file I/O with fallback mechanisms
- **Network Issues**: Timeout handling and retry logic

## 🎯 Use Cases

### Development and Testing
```bash
# Quick development cycle
./meshtastic_unified.py --discover                    # Find nodes
./meshtastic_unified.py --nodes !found_node --once --plot  # Test collection
```

### Production Monitoring
```bash
# Continuous monitoring setup
./meshtastic_unified.py --all-nodes --auto-plot --interval 300 \\
    --output /var/log/meshtastic/telemetry.csv \\
    --plot-outdir /var/www/html/meshtastic
```

### Data Analysis
```bash
# Generate fresh dashboards from existing data
./meshtastic_unified.py --nodes !abc123 --once --plot --regenerate-charts
```

## 🔧 Troubleshooting

### Common Issues

**"No nodes discovered"**
- Normal behavior without connected Meshtastic hardware
- Use `--discover` to verify available nodes

**"Plotting failed: ModuleNotFoundError: No module named 'pandas'"**
- Fixed in alpha version - uses correct Python interpreter automatically

**Dashboard not updating**
- Use `--regenerate-charts` to force refresh
- Check file permissions in output directory

### Debug Mode
```bash
# Enable verbose output for troubleshooting
./meshtastic_unified.py --discover --verbose
```

## 📝 Next Steps

1. **Run Discovery**: `./meshtastic_unified.py --discover`
2. **Test Collection**: `./meshtastic_unified.py --nodes [discovered_node] --once --plot`
3. **Setup Monitoring**: Configure continuous collection as needed
4. **Access Dashboard**: Open `plots/index.html` in your browser

The unified logger provides a complete, reliable solution for Meshtastic network monitoring with minimal setup and maximum functionality.
