meshtastic-telemetry-logger

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

Notes
- The script uses the `meshtastic` CLI (Python package) to perform requests; ensure the CLI is available in your environment.
- The `requirements.txt` lists plotting/data packages (pandas, numpy, matplotlib)."
