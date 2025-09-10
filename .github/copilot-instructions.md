# Meshtastic Logger Copilot Instructions

**CRITICAL: Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Repository Overview

Meshtastic Logger is a Python toolkit for collecting, logging, and visualizing telemetry and traceroute data from Meshtastic mesh network nodes. The repository has been refactored from a monolithic architecture to a modular design for better maintainability.

## Working Effectively

### Bootstrap and Setup
Run these commands in order to set up the development environment:

```bash
# Install Python dependencies - NEVER CANCEL: takes 30-60 seconds
pip3 install -r requirements.txt
```

**Timing:** Package installation takes 30-60 seconds on first install, ~1 second if already installed. NEVER CANCEL - wait for completion.

### Build and Test
```bash
# Run unit tests - takes ~2 seconds
python3 -m unittest tests.test_core_modules -v

# Verify main applications load correctly
python3 meshtastic_logger_refactored.py --help
python3 discover_nodes_refactored.py --help
```

**Important:** This application requires physical Meshtastic hardware devices to function fully. Without hardware, commands will fail gracefully in ~0.2-0.5 seconds with clear error messages.

### Run the Applications

**Refactored Version (Recommended):**
```bash
# Auto-discover and monitor all nodes (requires hardware)
python3 meshtastic_logger_refactored.py --all-nodes --once --plot

# Monitor specific nodes (requires hardware)  
python3 meshtastic_logger_refactored.py --nodes !abc123 !def456 --once --plot

# Node discovery only (requires hardware)
python3 discover_nodes_refactored.py --detailed
```

**Legacy Version (Compatibility):**
```bash
# Legacy main script
python3 meshtastic_telemetry_logger.py --all-nodes --once

# Legacy plotting
python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --regenerate-charts
```

**Hardware Dependency:** All data collection commands require actual Meshtastic devices connected via USB or network. Commands will fail gracefully in ~0.2-0.5 seconds and report "Failed to discover nodes" without hardware.

## Validation Scenarios

### Essential Validation (No Hardware Required)
Always run these validation steps after making changes:

```bash
# 1. Unit tests must pass - takes ~2 seconds
python3 -m unittest tests.test_core_modules -v

# 2. Applications must start and show help
python3 meshtastic_logger_refactored.py --help
python3 discover_nodes_refactored.py --help

# 3. Applications must handle missing hardware gracefully
timeout 10 python3 discover_nodes_refactored.py --detailed
# Should complete in ~0.2-0.5 seconds with "No nodes discovered" message
```

### Code Quality Validation
```bash
# Run linting with Trunk - NEVER CANCEL: may take 30-60 seconds for first run
trunk check

# Format code
trunk format

# Individual linters (if trunk is unavailable)
black .
isort .
ruff check .
```

## Architecture and Navigation

### Core Modules (`core/`)
**Always import from core modules in new code:**

- **`cli_utils.py`**: CLI command execution, validation (`validate_node_id`, `run_cli`)
- **`csv_utils.py`**: CSV handling (`setup_telemetry_csv`, `append_row`, `iso_now`)
- **`node_discovery.py`**: Network discovery (`discover_all_nodes`, `collect_nodes_detailed`)
- **`telemetry.py`**: Telemetry collection (`collect_telemetry_cli`, `collect_telemetry_batch`)
- **`traceroute.py`**: Network topology (`collect_traceroute_cli`, `get_network_topology`)
- **`config.py`**: Configuration management (`LoggerConfig`, `DEFAULT_CONFIG`)

### Main Scripts
- **`meshtastic_logger_refactored.py`**: **PREFERRED** - Clean, modular main logger
- **`discover_nodes_refactored.py`**: **PREFERRED** - Node discovery script
- **`meshtastic_telemetry_logger.py`**: Legacy monolithic implementation (keep for compatibility)

### Generated Output
- **CSV files**: `telemetry.csv`, `traceroute.csv` (gitignored)
- **HTML dashboards**: `plots/` directory (gitignored)
  - `index.html`: Main dashboard
  - `node_{id}/index.html`: Per-node pages
  - Various PNG charts

## Development Guidelines

### Code Changes
- **USE REFACTORED VERSION**: Always work with `meshtastic_logger_refactored.py` and `core/` modules
- **Import from core**: `from core import validate_node_id, collect_telemetry_cli`
- **Maintain compatibility**: Keep legacy scripts functional but prefer refactored versions
- **Follow modular design**: New functionality goes in appropriate core module

### Testing Requirements
```bash
# Always run before committing changes
python3 -m unittest tests.test_core_modules -v

# Add tests for new core module functions in tests/test_core_modules.py
# Test structure: TestCliUtils, TestCsvUtils, TestNodeDiscovery, etc.
```

### Hardware Limitations
- **No hardware simulation**: Cannot simulate Meshtastic devices in tests
- **Graceful failure expected**: Commands should timeout cleanly without hardware
- **Focus on unit tests**: Test individual functions, not end-to-end workflows
- **Validation approach**: Verify help text, imports, and error handling

## Common Tasks and File Locations

### Adding New Functionality
1. **Core logic**: Add to appropriate `core/` module
2. **CLI interface**: Update main scripts to use core functions
3. **Tests**: Add unit tests to `tests/test_core_modules.py`
4. **Documentation**: Update README.md usage examples

### Frequently Updated Files
- **`core/telemetry.py`**: When changing telemetry collection logic
- **`core/node_discovery.py`**: When modifying node discovery behavior
- **`meshtastic_logger_refactored.py`**: For main application workflow changes
- **`tests/test_core_modules.py`**: Always add tests for new core functions

### Configuration and Dependencies
- **`requirements.txt`**: Python package dependencies
- **`.trunk/trunk.yaml`**: Linting configuration (black, ruff, isort, bandit, etc.)
- **`core/config.py`**: Application configuration management
- **`.gitignore`**: Excludes generated CSV/HTML files and Python cache

## Troubleshooting

### Common Issues
1. **"meshtastic CLI not found"**: Run `pip3 install -r requirements.txt`
2. **"No nodes discovered"**: Expected without physical hardware
3. **Import errors**: Check Python path and ensure `core/` modules are present
4. **Linting failures**: Run `trunk format` then `trunk check`

### Environment Requirements
- **Python**: 3.10+ (tested with 3.12.3)
- **Package manager**: pip3
- **Internet access**: Required for initial dependency installation
- **Storage**: ~50MB for dependencies, variable for generated data

### Time Expectations
- **Package installation**: 30-60 seconds first time, ~1 second subsequent - NEVER CANCEL
- **Unit tests**: ~0.05 seconds (57ms)
- **Hardware commands**: 0.2-0.5 second graceful failure without devices
- **Linting (first run)**: 10-30 seconds - NEVER CANCEL

### Complete Workflow Example

**New Developer First-Time Setup:**
```bash
# 1. Setup environment
pip3 install -r requirements.txt  # 30-60s first time

# 2. Validate core functionality  
python3 -m unittest tests.test_core_modules -v  # ~0.05s

# 3. Test applications load
python3 meshtastic_logger_refactored.py --help
python3 discover_nodes_refactored.py --help

# 4. Test graceful hardware failure handling
timeout 10 python3 discover_nodes_refactored.py --detailed  # ~0.2s
timeout 10 python3 meshtastic_logger_refactored.py --all-nodes --once  # ~0.4s

# 5. Test core module imports
python3 -c "from core import validate_node_id, collect_telemetry_cli"
```

**Expected Results:**
- Dependencies install successfully
- All 7 unit tests pass 
- Help commands display usage information
- Hardware commands fail gracefully with clear "No nodes discovered" messages
- Core imports work without errors

## Quick Reference

### Essential Commands
```bash
# Setup
pip3 install -r requirements.txt

# Test
python3 -m unittest tests.test_core_modules -v

# Run (preferred)
python3 meshtastic_logger_refactored.py --all-nodes --once --plot

# Lint
trunk check && trunk format
```

### Key Files to Know
- `README.md`: User documentation and examples
- `REFACTORING_GUIDE.md`: Migration guide from legacy to refactored version
- `core/__init__.py`: Core module exports
- `requirements.txt`: Dependencies
- `tests/test_core_modules.py`: Unit tests