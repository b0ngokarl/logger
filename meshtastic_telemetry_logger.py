#!/usr/bin/env python3
"""
Meshtastic Telemetry + Traceroute Logger (v3)

- Telemetry: via CLI (compat), parses human-readable output robustly
- Traceroute: via CLI, parses forward/back paths with per-hop dB values
- Appends to two CSVs: telemetry_log.csv and traceroute_log.csv
- Works with serial (--serial /dev/ttyACM0 or /dev/ttyUSB0)
- Retries, ISO timestamps, fsync
"""
import argparse
import csv
import datetime as dt
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict

def iso_now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")

def ensure_header(csv_path: Path, header: List[str]):
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)

def append_row(csv_path: Path, row: List[object]):
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(row)
        f.flush()
        os.fsync(f.fileno())

# ---- Telemetry CLI parsing ----
RE_BATT = re.compile(r"Battery level:\s*([0-9.]+)%")
RE_VOLT = re.compile(r"Voltage:\s*([0-9.]+)\s*V")
RE_CHAN = re.compile(r"Total channel utilization:\s*([0-9.]+)%")
RE_AIR  = re.compile(r"Transmit air utilization:\s*([0-9.]+)%")
RE_UP   = re.compile(r"Uptime:\s*([0-9]+)\s*s")

def run_cli(cmd: List[str], timeout: int=30) -> Tuple[bool, str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output
    except subprocess.TimeoutExpired:
        return False, "[TIMEOUT]"

def collect_telemetry_cli(dest: str, serial_dev: Optional[str]=None, timeout: int=20) -> Optional[dict]:
    cmd = ["meshtastic", "--request-telemetry", "--dest", dest]
    if serial_dev:
        cmd += ["--port", serial_dev]
    ok, out = run_cli(cmd, timeout=timeout)
    if not ok:
        print(f"[WARN] Telemetry CLI failed for {dest}:\n{out}", file=sys.stderr)
        return None
    if "Telemetry received" not in out:
        print(f"[WARN] No telemetry marker in output for {dest}", file=sys.stderr)
        return None

    def grab(rx: re.Pattern, text: str) -> Optional[str]:
        m = rx.search(text)
        return m.group(1) if m else None

    return {
        "battery_pct": grab(RE_BATT, out),
        "voltage_v": grab(RE_VOLT, out),
        "channel_util_pct": grab(RE_CHAN, out),
        "air_tx_pct": grab(RE_AIR, out),
        "uptime_s": grab(RE_UP, out),
    }

# ---- Traceroute CLI parsing ----
RE_HOP = re.compile(r"(![0-9a-fA-F]+)\s*-->\s*(![0-9a-fA-F]+)\s*\(([+-]?[0-9.]+)\s*dB\)")
RE_FWD_HDR = re.compile(r"Route traced towards destination", re.IGNORECASE)
RE_BWD_HDR = re.compile(r"Route traced back to us", re.IGNORECASE)

def collect_traceroute_cli(dest: str, serial_dev: Optional[str]=None, timeout: int=30) -> Optional[Dict[str, List[Tuple[str,str,float]]]]:
    cmd = ["meshtastic", "--traceroute", dest]
    if serial_dev:
        cmd += ["--port", serial_dev]
    ok, out = run_cli(cmd, timeout=timeout)
    if not ok:
        print(f"[WARN] Traceroute CLI failed for {dest}:\n{out}", file=sys.stderr)
        return None

    # Split into forward/back sections heuristically
    lines = out.splitlines()
    fwd: List[Tuple[str,str,float]] = []
    bwd: List[Tuple[str,str,float]] = []
    section = None  # "fwd" | "bwd" | None

    for line in lines:
        if RE_FWD_HDR.search(line):
            section = "fwd"; continue
        if RE_BWD_HDR.search(line):
            section = "bwd"; continue
        m = RE_HOP.search(line)
        if m:
            a, b, val = m.group(1), m.group(2), float(m.group(3))
            if section == "bwd":
                bwd.append((a,b,val))
            else:
                # Default unspecified lines to forward (some versions may omit headers)
                fwd.append((a,b,val))

    if not fwd and not bwd:
        print(f"[WARN] No hops parsed for traceroute {dest}. Raw:\n{out}", file=sys.stderr)
        return None

    return {"forward": fwd, "back": bwd}

# ---- Main ----

def parse_args():
    p = argparse.ArgumentParser(description="Meshtastic telemetry+traceroute CSV logger")
    p.add_argument("--nodes", nargs="+", required=True, help="List of node IDs (e.g., !exampleA)")
    p.add_argument("--output", default="telemetry_log.csv", help="CSV output file (telemetry)")
    p.add_argument("--trace-output", default="traceroute_log.csv", help="CSV output file (traceroutes)")
    p.add_argument("--interval", type=int, default=60, help="Seconds between cycles (ignored with --once)")
    p.add_argument("--retries", type=int, default=1, help="Retries per node on timeout")
    p.add_argument("--serial", help="Serial device path, e.g. /dev/ttyACM0 or /dev/ttyUSB0")
    p.add_argument("--once", action="store_true", help="Collect exactly one cycle and exit")
    p.add_argument("--no-trace", action="store_true", help="Disable traceroute collection")
    p.add_argument("--no-plot", action="store_true", dest="no_plot", help="Disable automatic plotting after each cycle")
    p.add_argument("--plot-outdir", default="plots", help="Output directory to write plots (used when auto-plotting)")
    return p.parse_args()

_stop = False
def _sig_handler(signum, frame):
    global _stop
    _stop = True
    print("\n[INFO] Stopping...", file=sys.stderr)

def main():
    args = parse_args()
    tele_csv = Path(args.output)
    trace_csv = Path(args.trace_output)
    plot_outdir = Path(args.plot_outdir)

    ensure_header(tele_csv, ["timestamp","node","battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s"])
    ensure_header(trace_csv, ["timestamp","dest","direction","hop_index","from","to","link_db"])

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    while True:
        cycle_ts = iso_now()
        for node in args.nodes:
            # --- Telemetry ---
            tel = None
            attempt = 0
            while attempt <= args.retries:
                tel = collect_telemetry_cli(dest=node, serial_dev=args.serial)
                if tel: break
                attempt += 1
                if attempt <= args.retries:
                    time.sleep(0.8)
            if tel:
                append_row(tele_csv, [
                    cycle_ts, node,
                    tel.get("battery_pct"), tel.get("voltage_v"),
                    tel.get("channel_util_pct"), tel.get("air_tx_pct"),
                    tel.get("uptime_s")
                ])
                print(f"[OK] TEL {node} batt={tel.get('battery_pct')}% volt={tel.get('voltage_v')}V chan={tel.get('channel_util_pct')}% air={tel.get('air_tx_pct')}% up={tel.get('uptime_s')}s")
            else:
                print(f"[MISS] TEL {node}", file=sys.stderr)

            # --- Traceroute ---
            if not args.no_trace:
                tr = None
                attempt = 0
                while attempt <= args.retries:
                    tr = collect_traceroute_cli(dest=node, serial_dev=args.serial)
                    if tr: break
                    attempt += 1
                    if attempt <= args.retries:
                        time.sleep(0.8)
                if tr:
                    # forward
                    for i, (a,b,val) in enumerate(tr.get("forward", []), start=1):
                        append_row(trace_csv, [cycle_ts, node, "forward", i, a, b, val])
                    # back
                    for i, (a,b,val) in enumerate(tr.get("back", []), start=1):
                        append_row(trace_csv, [cycle_ts, node, "back", i, a, b, val])
                    print(f"[OK] TRC {node} hops_fwd={len(tr.get('forward', []))} hops_back={len(tr.get('back', []))}")
                else:
                    print(f"[MISS] TRC {node}", file=sys.stderr)

        if args.once or _stop:
            # After a single run, optionally generate plots
            if not args.no_plot:
                try:
                    # Prefer using the same virtualenv python if available
                    py = sys.executable
                    plot_script = Path(__file__).parent / "plot_meshtastic.py"
                    cmd = [py, str(plot_script), "--telemetry", str(tele_csv), "--traceroute", str(trace_csv), "--outdir", str(plot_outdir)]
                    print(f"[INFO] Running plot script: {' '.join(cmd)}")
                    subprocess.run(cmd, check=True)
                    print(f"[INFO] Plots written to {plot_outdir}")
                except subprocess.CalledProcessError as e:
                    print(f"[WARN] Plot script failed: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"[WARN] Unexpected error running plot script: {e}", file=sys.stderr)
            break
        # sleep until next cycle
        for _ in range(int(args.interval*10)):
            if _stop: break
            time.sleep(0.1)
        if _stop:
            break

if __name__ == "__main__":
    main()
