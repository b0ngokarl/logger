# meshtastic-telemetry-logger

This repository contains a small Meshtastic telemetry & traceroute logger and plotter.

Quick start

1. Create and activate a virtualenv in the project root (optional but recommended):

   python -m venv .venv
   source .venv/bin/activate

2. Install runtime requirements:

   pip install -r requirements.txt


3. Run the logger once (replace nodes with your node IDs):

   python meshtastic_telemetry_logger.py --nodes !exampleA !exampleB --once

   This will append rows to `telemetry.csv` and `traceroute.csv`.

4. By default the logger will automatically run `plot_meshtastic.py` after each `--once` run and write output into the `plots/` directory. Use `--no-plot` to disable automatic plotting.

Useful options:
  --interval N        Run continuously every N seconds between cycles
  --once              Run a single cycle and exit
  --no-plot           Skip automatic plotting after each run
  --plot-outdir PATH  Directory for plot output (default: plots)
  --serial PATH       Serial device path (e.g., /dev/ttyACM0)
  --no-trace          Disable traceroute collection
  --retries N         Number of retries per node on timeout

## Examples

### Basic single run
```bash
python meshtastic_telemetry_logger.py --nodes !exampleA !exampleB --once
```

### Continuous monitoring with custom interval
```bash
python meshtastic_telemetry_logger.py --nodes !exampleA !exampleB --interval 300
```

### Using serial connection
```bash
python meshtastic_telemetry_logger.py --nodes !exampleA !exampleB --serial /dev/ttyACM0 --once
```

### Disable automatic plotting
```bash
python meshtastic_telemetry_logger.py --nodes !exampleA !exampleB --once --no-plot
```

### Custom output files
```bash
python meshtastic_telemetry_logger.py --nodes !exampleA !exampleB --output my_telemetry.csv --trace-output my_traceroute.csv --once
```

### Generate plots from existing data
```bash
python plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --outdir plots
```

### Merge multiple CSV files for plotting
```bash
python plot_meshtastic.py --telemetry telemetry_*.csv --traceroute traceroute_*.csv --outdir plots
```

Notes
- The script uses the `meshtastic` CLI (Python package) to perform requests; ensure the CLI is available in your environment.
- The `requirements.txt` lists plotting/data packages (pandas, numpy, matplotlib)."
