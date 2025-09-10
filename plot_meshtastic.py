#!/usr/bin/env python3
"""
Plot Meshtastic telemetry & traceroute CSVs
- Merges multiple CSV inputs (e.g., mix of --once and --interval runs)
- De-duplicates rows, sorts by time
- Per-node dashboards, traceroute time-series, topology snapshots
- Diagnostics to verify merged ranges
- Matplotlib only (no seaborn), single-plot figures
- Updated to use standardized HTML templates for consistent styling

Usage examples:
    # Single files
    python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --outdir plots

    # Merge many (e.g., rotated or separate runs)
    python3 plot_meshtastic.py \
        --telemetry telemetry.csv telemetry_*.csv \
        --traceroute traceroute.csv traceroute_*.csv \
        --outdir plots
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
from datetime import datetime

# Add core module to path for template imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))
try:
    from html_templates import get_html_template, format_value, create_battery_bar, create_status_indicator
    TEMPLATES_AVAILABLE = True
except ImportError:
    print("[WARN] Could not import html_templates, using fallback styling", file=sys.stderr)
    TEMPLATES_AVAILABLE = False

def ensure_outdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def create_timestamped_output_dir(base_outdir: Path) -> Path:
    """Create a timestamped output directory and symlink to 'latest'"""
    timestamp = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    timestamped_dir = base_outdir / timestamp
    latest_link = base_outdir / "latest"
    
    # Create the timestamped directory
    timestamped_dir.mkdir(parents=True, exist_ok=True)
    
    # Update the 'latest' symlink (remove existing one first)
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(timestamp, target_is_directory=True)
    
    return timestamped_dir

def parse_args():
    ap = argparse.ArgumentParser(description="Plot Meshtastic telemetry & traceroute CSVs (v3, merge-aware)")
    ap.add_argument("--telemetry", nargs="+", required=True, help="One or more telemetry CSVs")
    ap.add_argument("--traceroute", nargs="+", required=True, help="One or more traceroute CSVs")
    ap.add_argument("--outdir", default="plots", help="Output directory for PNGs and HTML")
    ap.add_argument("--regenerate-charts", action="store_true", help="Force regeneration of all charts")
    ap.add_argument("--preserve-history", action="store_true", help="Create timestamped directory and preserve history")
    return ap.parse_args()

def read_merge_telemetry(paths):
    need = ["timestamp","node","battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s",
           "temperature_c","humidity_pct","pressure_hpa","iaq","lux","current_ma",
           "ch1_voltage_v","ch1_current_ma","ch2_voltage_v","ch2_current_ma",
           "ch3_voltage_v","ch3_current_ma","ch4_voltage_v","ch4_current_ma"]
    frames = []
    for p in paths:
        df = pd.read_csv(p)
        missing = [c for c in need if c not in df.columns]
        if missing:
            print(f"[WARN] Skip {p}: missing columns {missing}")
            continue
        frames.append(df[need].copy())
    if not frames:
        return pd.DataFrame(columns=need)

    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    for col in ["battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s",
               "temperature_c","humidity_pct","pressure_hpa","iaq","lux","current_ma",
               "ch1_voltage_v","ch1_current_ma","ch2_voltage_v","ch2_current_ma",
               "ch3_voltage_v","ch3_current_ma","ch4_voltage_v","ch4_current_ma"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    # Drop duplicates (identical timestamp+node)
    df = df.drop_duplicates(subset=["timestamp","node"])
    df = df.sort_values(["node","timestamp"])
    return df

def read_merge_traceroute(paths):
    need = ["timestamp","dest","direction","hop_index","from","to","link_db"]
    frames = []
    for p in paths:
        df = pd.read_csv(p)
        missing = [c for c in need if c not in df.columns]
        if missing:
            print(f"[WARN] Skip {p}: missing columns {missing}")
            continue
        frames.append(df[need].copy())
    if not frames:
        return pd.DataFrame(columns=need)

    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df["hop_index"] = pd.to_numeric(df["hop_index"], errors="coerce")
    df["link_db"] = pd.to_numeric(df["link_db"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    # Drop duplicates (identical route edge at same time)
    df = df.drop_duplicates(subset=["timestamp","dest","direction","hop_index","from","to"])
    df = df.sort_values(["dest","direction","timestamp","hop_index"])
    return df

def _now_iso():
    return datetime.now().isoformat(sep=' ', timespec='seconds')

def log_info(msg):
    print(f"[INFO] {_now_iso()} {msg}", flush=True)

def log_warn(msg):
    print(f"[WARN] {_now_iso()} {msg}", file=sys.stderr, flush=True)

def _fmt_ts(ts):
    try:
        return pd.to_datetime(ts).strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return str(ts)

def diagnostics(df_tele, df_trace, outdir: Path, sources_tele, sources_trace):
    # Calculate estimated battery runtime for each node
    est_runtimes = {}
    for node, part in df_tele.groupby("node"):
        batt_data = part["battery_pct"].dropna()
        if len(batt_data) > 1:
            ts_seconds = part["timestamp"].astype(int) / 10**9
            x_clean = ts_seconds[part["battery_pct"].notna()]
            y_clean = batt_data
            slope, intercept = np.polyfit(x_clean, y_clean, 1)
            if slope < 0:
                current_batt = y_clean.iloc[-1]
                time_to_zero_sec = current_batt / abs(slope)
                time_to_zero_days = time_to_zero_sec / 3600 / 24
                est_runtimes[node] = f"{time_to_zero_days:.1f} days"

    # Produce both plain-text and a simple responsive HTML diagnostics page.
    lines = []
    lines.append("Diagnostics (merged)")
    lines.append("====================")
    lines.append(f"Generated: {_now_iso()}")
    lines.append("")
    lines.append("Sources telemetry:")
    for s in sources_tele:
        lines.append(f"  - {s}")
    lines.append("Sources traceroute:")
    for s in sources_trace:
        lines.append(f"  - {s}")
    lines.append("")
    lines.append("TELEMETRY:")
    lines.append(f"  rows (merged, unique): {len(df_tele)}")
    if len(df_tele):
        nodes = sorted(map(str, df_tele['node'].dropna().unique()))
        lines.append(f"  nodes: {', '.join(nodes)}")
        lines.append(f"  time span: {_fmt_ts(df_tele['timestamp'].min())} .. {_fmt_ts(df_tele['timestamp'].max())}")
        for c in ["battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s"]:
            lines.append(f"  NaNs {c}: {int(df_tele[c].isna().sum())}")
    lines.append("")
    lines.append("TRACEROUTE:")
    lines.append(f"  rows (merged, unique): {len(df_trace)}")
    if len(df_trace):
        lines.append(f"  dests: {', '.join(sorted(map(str, df_trace['dest'].dropna().unique())))}")
        lines.append(f"  directions: {', '.join(sorted(map(str, df_trace['direction'].dropna().unique())))}")
        lines.append(f"  time span: {_fmt_ts(df_trace['timestamp'].min())} .. {_fmt_ts(df_trace['timestamp'].max())}")

    diag_path = outdir / "diagnostics.txt"
    diag_path.write_text("\n".join(lines), encoding="utf-8")
    log_info(f"Wrote diagnostics to {diag_path}")

    # Build diagnostics HTML content using standardized template
    content = _build_diagnostics_content(df_tele, df_trace, sources_tele, sources_trace, est_runtimes)
    
    # Navigation links
    navigation = [
        {'url': 'index.html', 'text': '🏠 Main Dashboard'},
        {'url': 'nodes.html', 'text': '🌐 All Nodes'},
        {'url': 'dashboards.html', 'text': '📊 Node Details'}
    ]
    
    # Use standardized template if available
    if TEMPLATES_AVAILABLE:
        html = get_html_template(
            title="🔍 Data Diagnostics",
            content=content,
            navigation_links=navigation
        )
    else:
        # Fallback HTML
        html = _fallback_diagnostics_html(df_tele, df_trace, sources_tele, sources_trace, est_runtimes)

    (outdir / "diagnostics.html").write_text(html, encoding="utf-8")
    log_info(f"Wrote diagnostics HTML to {(outdir / 'diagnostics.html')}")

def _build_diagnostics_content(df_tele, df_trace, sources_tele, sources_trace, est_runtimes):
    """Build the main content for the diagnostics page."""
    
    content_parts = []
    
    # Data sources section
    sources_list = []
    for s in sources_tele:
        sources_list.append(f"<li><strong>Telemetry:</strong> {s}</li>")
    for s in sources_trace:
        sources_list.append(f"<li><strong>Traceroute:</strong> {s}</li>")
    
    content_parts.append(f"""
    <div class="section">
        <h2>📁 Data Sources</h2>
        <ul>
            {''.join(sources_list)}
        </ul>
    </div>
    """)
    
    # Summary statistics
    tele_rows = len(df_tele)
    trace_rows = len(df_trace)
    tele_nodes = len(df_tele['node'].dropna().unique()) if tele_rows else 0
    trace_dests = len(df_trace['dest'].dropna().unique()) if trace_rows else 0
    
    content_parts.append(f"""
    <div class="section">
        <h2>📊 Summary Statistics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-name">Telemetry Rows</div>
                <div class="metric-value">{tele_rows}</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Traceroute Rows</div>
                <div class="metric-value">{trace_rows}</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Telemetry Nodes</div>
                <div class="metric-value">{tele_nodes}</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">Traceroute Destinations</div>
                <div class="metric-value">{trace_dests}</div>
            </div>
        </div>
    </div>
    """)
    
    # Telemetry details
    if len(df_tele):
        tele_rows_html = []
        for node, part in df_tele.groupby("node"):
            last = part["timestamp"].max()
            rows = len(part)
            latest_batt = part.sort_values("timestamp").iloc[-1]["battery_pct"] if rows else ""
            latest_volt = part.sort_values("timestamp").iloc[-1]["voltage_v"] if rows else ""
            latest_runtime = est_runtimes.get(node, "")
            
            # Format values with proper handling of empty data
            batt_display = f"{latest_batt:.1f}%" if latest_batt != "" and pd.notna(latest_batt) else "N/A"
            volt_display = f"{latest_volt:.2f}V" if latest_volt != "" and pd.notna(latest_volt) else "N/A"
            runtime_display = latest_runtime if latest_runtime else "N/A"
            
            tele_rows_html.append(f"""
                <tr>
                    <td style="font-family: monospace;">{node}</td>
                    <td><span class="timestamp">{_fmt_ts(last)}</span></td>
                    <td style="text-align: center;">{rows}</td>
                    <td>{batt_display}</td>
                    <td>{volt_display}</td>
                    <td>{runtime_display}</td>
                </tr>
            """)
        
        content_parts.append(f"""
        <div class="section">
            <h2>📡 Telemetry Details</h2>
            <table class="info-table">
                <thead>
                    <tr>
                        <th>Node</th>
                        <th>Last Seen</th>
                        <th>Rows</th>
                        <th>Latest Battery</th>
                        <th>Latest Voltage</th>
                        <th>Est. Runtime</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(tele_rows_html)}
                </tbody>
            </table>
        </div>
        """)
    
    # Traceroute details  
    if len(df_trace):
        trace_rows_html = []
        for (dest, direction), part in df_trace.groupby(["dest","direction"]):
            last = part["timestamp"].max()
            rows = len(part)
            trace_rows_html.append(f"""
                <tr>
                    <td style="font-family: monospace;">{dest}</td>
                    <td style="text-transform: capitalize;">{direction}</td>
                    <td><span class="timestamp">{_fmt_ts(last)}</span></td>
                    <td style="text-align: center;">{rows}</td>
                </tr>
            """)
        
        content_parts.append(f"""
        <div class="section">
            <h2>🗺️ Traceroute Details</h2>
            <table class="info-table">
                <thead>
                    <tr>
                        <th>Destination</th>
                        <th>Direction</th>
                        <th>Last Seen</th>
                        <th>Rows</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(trace_rows_html)}
                </tbody>
            </table>
        </div>
        """)
    
    # Data quality section
    if len(df_tele):
        quality_info = []
        for c in ["battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s"]:
            nan_count = int(df_tele[c].isna().sum())
            total_count = len(df_tele)
            percentage = (nan_count / total_count * 100) if total_count > 0 else 0
            quality_info.append(f"""
                <tr>
                    <td>{c.replace('_', ' ').title()}</td>
                    <td style="text-align: center;">{nan_count}</td>
                    <td style="text-align: center;">{percentage:.1f}%</td>
                </tr>
            """)
        
        content_parts.append(f"""
        <div class="section">
            <h2>📋 Data Quality</h2>
            <table class="info-table">
                <thead>
                    <tr>
                        <th>Field</th>
                        <th>Missing Values</th>
                        <th>Missing %</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(quality_info)}
                </tbody>
            </table>
        </div>
        """)
    
    return '\n'.join(content_parts)

def _fallback_diagnostics_html(df_tele, df_trace, sources_tele, sources_trace, est_runtimes):
    """Fallback HTML for diagnostics if templates are not available."""
    
    html_lines = [
        "<!doctype html>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>🔍 Data Diagnostics</title>",
        "<style>body{font-family:Arial,Helvetica,sans-serif;margin:16px}table{border-collapse:collapse;width:100%;max-width:900px}td,th{border:1px solid #ddd;padding:6px}th{background:#f3f3f3;text-align:left}</style>",
        f"<h1>🔍 Data Diagnostics (generated {_now_iso()})</h1>",
        "<h2>Sources</h2>",
        "<ul>",
    ]
    for s in sources_tele:
        html_lines.append(f"<li>Telemetry: {s}</li>")
    for s in sources_trace:
        html_lines.append(f"<li>Traceroute: {s}</li>")
    html_lines.append("</ul>")

    if len(df_tele):
        html_lines.append("<h2>Telemetry summary</h2>")
        html_lines.append("<table>")
        html_lines.append("<tr><th>Node</th><th>Last seen</th><th>Rows</th><th>Latest battery</th><th>Latest voltage</th><th>Est. runtime</th></tr>")
        for node, part in df_tele.groupby("node"):
            last = part["timestamp"].max()
            rows = len(part)
            latest_batt = part.sort_values("timestamp").iloc[-1]["battery_pct"] if rows else ""
            latest_volt = part.sort_values("timestamp").iloc[-1]["voltage_v"] if rows else ""
            latest_runtime = est_runtimes.get(node, "")
            html_lines.append(f"<tr><td>{node}</td><td>{_fmt_ts(last)}</td><td>{rows}</td><td>{latest_batt}</td><td>{latest_volt}</td><td>{latest_runtime}</td></tr>")
        html_lines.append("</table>")

    if len(df_trace):
        html_lines.append("<h2>Traceroute summary</h2>")
        html_lines.append("<table>")
        html_lines.append("<tr><th>Dest</th><th>Direction</th><th>Last seen</th><th>Rows</th></tr>")
        for (dest, direction), part in df_trace.groupby(["dest","direction"]):
            last = part["timestamp"].max()
            rows = len(part)
            html_lines.append(f"<tr><td>{dest}</td><td>{direction}</td><td>{_fmt_ts(last)}</td><td>{rows}</td></tr>")
        html_lines.append("</table>")

    return "\n".join(html_lines)

def plot_per_node_dashboards(df: pd.DataFrame, outdir: Path, force_regenerate=False):
    metrics = [
        # Basic device metrics
        ("battery_pct", "Battery (%)", "battery"),
        ("voltage_v", "Voltage (V)", "voltage"),
        ("channel_util_pct", "Channel Utilization (%)", "channel_util"),
        ("air_tx_pct", "Air TX Utilization (%)", "air_tx"),
        ("uptime_s", "Uptime (hours)", "uptime_hours"),
        # Environment sensors
        ("temperature_c", "Temperature (°C)", "temperature"),
        ("humidity_pct", "Humidity (%)", "humidity"),
        ("pressure_hpa", "Pressure (hPa)", "pressure"),
        ("iaq", "Air Quality Index", "iaq"),
        ("lux", "Light (Lux)", "lux"),
        # Power monitoring  
        ("current_ma", "Current (mA)", "current"),
        ("ch1_voltage_v", "Ch1 Voltage (V)", "ch1_voltage"),
        ("ch1_current_ma", "Ch1 Current (mA)", "ch1_current"),
        ("ch2_voltage_v", "Ch2 Voltage (V)", "ch2_voltage"),
        ("ch2_current_ma", "Ch2 Current (mA)", "ch2_current"),
        ("ch3_voltage_v", "Ch3 Voltage (V)", "ch3_voltage"),
        ("ch3_current_ma", "Ch3 Current (mA)", "ch3_current"),
        ("ch4_voltage_v", "Ch4 Voltage (V)", "ch4_voltage"),
        ("ch4_current_ma", "Ch4 Current (mA)", "ch4_current"),
    ]
    nodes = sorted(df["node"].dropna().unique())
    dashboards = {}
    for node in nodes:
        part = df[df["node"] == node].sort_values("timestamp")
        if part.empty:
            continue
        node_dir = outdir / f"node_{str(node).replace('!','')}"
        node_dir.mkdir(parents=True, exist_ok=True)
        imgs = []
        for col, ylabel, slug in metrics:
            y = part[col]
            x = part["timestamp"]
            if col == "uptime_s":
                y = y / 3600.0
            if y.dropna().empty:
                continue
                
            fname = node_dir / f"{slug}.png"
            # Skip regenerating if file exists and force_regenerate is False
            if not force_regenerate and fname.exists():
                imgs.append(fname.name)
                continue
                
            plt.figure()
            plt.plot(x, y)
            plt.xlabel("Time")
            plt.ylabel(ylabel)
            plt.title(f"{node} - {ylabel}")
            if col == "battery_pct" and len(y.dropna()) > 1:
                x_seconds = x.astype(int) / 10**9
                y_clean = y.dropna()
                x_clean = x_seconds[y.notna()]
                slope, intercept = np.polyfit(x_clean, y_clean, 1)
                if slope < 0:
                    current_batt = y_clean.iloc[-1]
                    time_to_zero_sec = current_batt / abs(slope)
                    time_to_zero_days = time_to_zero_sec / 3600 / 24
                    plt.text(0.05, 0.95, f'Est. runtime: {time_to_zero_days:.1f} days', transform=plt.gca().transAxes, fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            plt.tight_layout()
            plt.savefig(fname)
            plt.close()
            imgs.append(fname.name)
        if imgs:
            # Calculate estimated battery runtime
            est_runtime = ""
            batt_data = part["battery_pct"].dropna()
            if len(batt_data) > 1:
                ts_seconds = part["timestamp"].astype(int) / 10**9
                x_clean = ts_seconds[part["battery_pct"].notna()]
                y_clean = batt_data
                slope, intercept = np.polyfit(x_clean, y_clean, 1)
                if slope < 0:
                    current_batt = y_clean.iloc[-1]
                    time_to_zero_sec = current_batt / abs(slope)
                    time_to_zero_days = time_to_zero_sec / 3600 / 24
                    est_runtime = f" &nbsp;|&nbsp; Est. runtime: {time_to_zero_days:.1f} days"

            # Build a slightly nicer responsive HTML per-node page with a small summary
            latest = part.sort_values("timestamp").iloc[-1]
            last_seen = _fmt_ts(latest["timestamp"])
            latest_batt = latest.get("battery_pct", "")
            latest_volt = latest.get("voltage_v", "")
            html = [
                "<!doctype html>",
                "<meta charset='utf-8'>",
                "<meta name='viewport' content='width=device-width,initial-scale=1'>",
                f"<title>Dashboard {node}</title>",
                "<style>body{font-family:Arial,Helvetica,sans-serif;margin:12px}img{max-width:100%;height:auto;border:1px solid #ddd;padding:4px;background:#fff} .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}</style>",
                f"<h1>Node {node}</h1>",
                f"<p>Last seen: {last_seen} &nbsp;|&nbsp; Battery: {latest_batt} &nbsp;|&nbsp; Voltage: {latest_volt}{est_runtime}</p>",
                "<div class='grid'>"
            ]
            for img in imgs:
                title = img.replace(".png","").replace("_"," ").title()
                html.append(f"<figure><figcaption>{title}</figcaption><a href='{img}'><img src='{img}' alt='{img}'></a></figure>")
            html.append("</div>")
            html.append("<p><a href='../index.html'>Back to index</a></p>")
            (node_dir / "index.html").write_text("\n".join(html), encoding="utf-8")
            dashboards[node] = node_dir
    if dashboards:
        lines = ["<!doctype html><meta charset='utf-8'><title>Per-Node Dashboards</title><h1>Per-Node Dashboards</h1><ul>"]
        for node, p in dashboards.items():
            rel = p.name + "/index.html"
            lines.append(f"<li><a href='{rel}'>Node {node}</a></li>")
        lines.append("</ul>")
        (outdir / "dashboards.html").write_text("\n".join(lines), encoding="utf-8")

def plot_traceroute_timeseries(df: pd.DataFrame, outdir: Path):
    if df.empty:
        return
    hops = (df.groupby(["timestamp","dest","direction"])["hop_index"]
              .max()
              .reset_index()
              .rename(columns={"hop_index":"hop_count"}))
    if not hops.empty:
        plt.figure()
        for key, part in hops.groupby(["dest","direction"]):
            label = f"{key[0]}-{key[1]}"
            plt.plot(part["timestamp"], part["hop_count"], label=label)
        plt.xlabel("Time")
        plt.ylabel("Hop count")
        plt.title("Traceroute: Hop count over time")
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / "traceroute_hops.png")
        plt.close()

    bottleneck = (df.groupby(["timestamp","dest","direction"])["link_db"]
                    .min()
                    .reset_index()
                    .rename(columns={"link_db":"bottleneck_db"}))
    if not bottleneck.empty:
        plt.figure()
        for key, part in bottleneck.groupby(["dest","direction"]):
            label = f"{key[0]}-{key[1]}"
            plt.plot(part["timestamp"], part["bottleneck_db"], label=label)
        plt.xlabel("Time")
        plt.ylabel("Bottleneck link (dB)")
        plt.title("Traceroute: Bottleneck link dB over time (lower is worse)")
        plt.legend()
        plt.tight_layout()
        plt.savefig(outdir / "traceroute_bottleneck_db.png")
        plt.close()

def _circular_layout(nodes: list, radius: float=1.0):
    n = len(nodes)
    coords = {}
    for i, node in enumerate(nodes):
        theta = 2*np.pi*i/max(n,1)
        coords[node] = (radius*np.cos(theta), radius*np.sin(theta))
    return coords

def plot_topology_snapshots(df: pd.DataFrame, outdir: Path):
    if df.empty:
        return
    latest = (df.groupby(["dest","direction"])["timestamp"].max().reset_index()
                .rename(columns={"timestamp":"ts"}))
    merged = df.merge(latest, on=["dest","direction"], how="inner")
    merged = merged[merged["timestamp"] == merged["ts"]]

    for (dest, direction), part in merged.groupby(["dest","direction"]):
        if part.empty:
            continue
        edges = list(zip(part["from"].astype(str), part["to"].astype(str), part["link_db"].astype(float)))
        nodes = sorted(set(part["from"]).union(set(part["to"])))
        pos = _circular_layout(nodes, radius=1.0)

        plt.figure()
        ax = plt.gca()
        for n in nodes:
            x,y = pos[n]
            ax.scatter([x],[y])
            ax.text(x, y, n, ha="center", va="bottom", fontsize=8)
        for a,b,db in edges:
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            ax.plot([x1,x2],[y1,y2])
            mx, my = (x1+x2)/2.0, (y1+y2)/2.0
            ax.text(mx, my, f"{db:.2f} dB", ha="center", va="center", fontsize=8)
        ax.set_aspect("equal", adjustable="datalim")
        ax.axis("off")
        plt.title(f"Topology ({direction}) latest for {dest}")
        plt.tight_layout()
        fname = outdir / f"topology_{dest.replace('!','')}_{direction}.png"
        plt.savefig(fname, dpi=150)
        plt.close()

def write_comprehensive_nodes_list(tele_df: pd.DataFrame, trace_df: pd.DataFrame, outdir: Path):
    """Create comprehensive nodes.html with status indicators and statistics using standardized template"""
    
    # Get all unique nodes from both datasets
    tele_nodes = set(tele_df['node'].dropna().unique()) if not tele_df.empty else set()
    trace_nodes = set() 
    if not trace_df.empty:
        # Get nodes from traceroute data (from both source and destination)
        for col in ['from', 'to', 'dest', 'source']:
            if col in trace_df.columns:
                trace_nodes.update(trace_df[col].dropna().unique())
    
    all_nodes = tele_nodes.union(trace_nodes)
    node_stats = []
    
    for node in sorted(all_nodes):
        stats = {
            'node': node,
            'has_telemetry': node in tele_nodes,
            'has_routing': node in trace_nodes,
            'last_seen': None,
            'battery_pct': None,
            'status': '🔴',  # Default to stale
            'status_text': 'Stale',
            'status_class': 'status-stale'
        }
        
        # Get latest telemetry data for this node
        if not tele_df.empty and node in tele_nodes:
            node_tele = tele_df[tele_df['node'] == node].copy()
            if not node_tele.empty:
                # Convert timestamp to datetime if it's not already
                node_tele['datetime'] = pd.to_datetime(node_tele['timestamp'])
                latest = node_tele.loc[node_tele['datetime'].idxmax()]
                
                stats['last_seen'] = latest['datetime'].strftime('%Y-%m-%d %H:%M:%S')
                stats['battery_pct'] = latest.get('battery_pct', None)
                
                # Calculate status based on last seen time
                current_naive = pd.Timestamp.now().tz_localize(None) if pd.Timestamp.now().tz else pd.Timestamp.now()
                latest_naive = latest['datetime'].tz_localize(None) if hasattr(latest['datetime'], 'tz') and latest['datetime'].tz else latest['datetime']
                hours_since = (current_naive - latest_naive).total_seconds() / 3600
                if hours_since < 1:
                    stats['status'] = '🟢'
                    stats['status_text'] = 'Active'
                    stats['status_class'] = 'status-active'
                elif hours_since < 24:
                    stats['status'] = '🟡'
                    stats['status_text'] = 'Recent'
                    stats['status_class'] = 'status-recent'
        
        node_stats.append(stats)
    
    # Build the content using standardized components
    content = _build_nodes_list_content(node_stats, all_nodes, tele_nodes, trace_nodes)
    
    # Navigation links
    navigation = [
        {'url': 'index.html', 'text': '🏠 Main Dashboard'},
        {'url': 'dashboards.html', 'text': '📊 Node Details'},
        {'url': 'diagnostics.html', 'text': '🔍 Diagnostics'}
    ]
    
    # Use standardized template if available
    if TEMPLATES_AVAILABLE:
        html = get_html_template(
            title="🌐 Meshtastic Network Nodes",
            content=content,
            navigation_links=navigation
        )
    else:
        # Fallback HTML
        html = _fallback_nodes_html(node_stats, all_nodes, tele_nodes, trace_nodes)
    
    (outdir / "nodes.html").write_text(html, encoding="utf-8")
    log_info(f"Wrote comprehensive nodes list to {(outdir / 'nodes.html')}")

def _build_nodes_list_content(node_stats, all_nodes, tele_nodes, trace_nodes):
    """Build the main content for the nodes list page."""
    
    # Summary statistics
    total_nodes = len(all_nodes)
    telemetry_nodes = len(tele_nodes)
    routing_nodes = len(trace_nodes)
    active_nodes = len([s for s in node_stats if s['status'] == '🟢'])
    
    # Build statistics cards
    stats_content = f"""
    <div class="section">
        <h2>📊 Network Summary</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-name">Total Nodes</div>
                <div class="metric-value">{total_nodes}</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">📊 Telemetry Active</div>
                <div class="metric-value">{telemetry_nodes}</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">🔗 Routing Active</div>
                <div class="metric-value">{routing_nodes}</div>
            </div>
            <div class="metric-card">
                <div class="metric-name">🟢 Currently Active</div>
                <div class="metric-value">{active_nodes}</div>
            </div>
        </div>
    </div>
    """
    
    # Build nodes table
    rows_html = []
    for stats in node_stats:
        # Battery visualization
        battery_cell = ""
        if stats['battery_pct'] is not None:
            if TEMPLATES_AVAILABLE:
                battery_cell = create_battery_bar(stats['battery_pct'])
            else:
                battery_pct = stats['battery_pct']
                battery_color = "#4CAF50" if battery_pct > 75 else "#FF9800" if battery_pct > 25 else "#F44336"
                battery_cell = f"""
                    <div style="display: flex; align-items: center;">
                        <div style="width: 60px; height: 10px; background: #ddd; border-radius: 5px; margin-right: 8px; overflow: hidden;">
                            <div style="width: {battery_pct}%; height: 100%; background: {battery_color};"></div>
                        </div>
                        <span>{battery_pct:.1f}%</span>
                    </div>
                """
        else:
            battery_cell = '<span class="empty-value">N/A</span>'
        
        # Status indicator
        if TEMPLATES_AVAILABLE:
            status_html = f'<span class="status-indicator {stats["status_class"]}">{stats["status"]} {stats["status_text"]}</span>'
        else:
            status_html = f'{stats["status"]} {stats["status_text"]}'
        
        # Icons for telemetry and routing
        telemetry_icon = "📊" if stats['has_telemetry'] else "❌"
        routing_icon = "🔗" if stats['has_routing'] else "❌"
        last_seen = stats['last_seen'] or "Unknown"
        
        # Node link - prefer dashboards link if available
        node_link = f'<a href="dashboards.html#{stats["node"]}" style="font-family: monospace; color: #2196F3; text-decoration: none;">{stats["node"]}</a>'
        
        rows_html.append(f"""
            <tr>
                <td>{node_link}</td>
                <td>{status_html}</td>
                <td><span class="timestamp">{last_seen}</span></td>
                <td>{battery_cell}</td>
                <td style="text-align: center;">{telemetry_icon}</td>
                <td style="text-align: center;">{routing_icon}</td>
            </tr>
        """)
    
    table_content = f"""
    <div class="section">
        <h2>📋 Node List</h2>
        <input type="text" class="search-box" placeholder="🔍 Search nodes..." onkeyup="filterNodes()">
        
        <table id="nodesTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)" style="cursor: pointer;">Node ID ↕️</th>
                    <th onclick="sortTable(1)" style="cursor: pointer;">Status ↕️</th>
                    <th onclick="sortTable(2)" style="cursor: pointer;">Last Seen ↕️</th>
                    <th>🔋 Battery</th>
                    <th>📊 Telemetry</th>
                    <th>🔗 Routing</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """
    
    # JavaScript for search and sort functionality
    javascript_content = """
    <script>
        function filterNodes() {
            const input = document.querySelector('.search-box');
            const filter = input.value.toUpperCase();
            const table = document.getElementById('nodesTable');
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {
                const row = rows[i];
                const nodeId = row.getElementsByTagName('td')[0];
                if (nodeId) {
                    const txtValue = nodeId.textContent || nodeId.innerText;
                    row.style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
                }
            }
        }
        
        function sortTable(columnIndex) {
            const table = document.getElementById('nodesTable');
            let rows = Array.from(table.rows).slice(1);
            const isAscending = table.getAttribute('data-sort-direction') !== 'asc';
            
            rows.sort((a, b) => {
                const aText = a.cells[columnIndex].textContent.trim();
                const bText = b.cells[columnIndex].textContent.trim();
                
                if (columnIndex === 2) { // Date column
                    return isAscending ? 
                        new Date(aText) - new Date(bText) : 
                        new Date(bText) - new Date(aText);
                }
                
                return isAscending ? 
                    aText.localeCompare(bText) : 
                    bText.localeCompare(aText);
            });
            
            rows.forEach(row => table.appendChild(row));
            table.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
        }
    </script>
    """
    
    return stats_content + table_content + javascript_content

def _fallback_nodes_html(node_stats, all_nodes, tele_nodes, trace_nodes):
    """Fallback HTML for nodes list if templates are not available."""
    total_nodes = len(all_nodes)
    telemetry_nodes = len(tele_nodes)
    routing_nodes = len(trace_nodes)
    
    rows_html = []
    for stats in node_stats:
        battery_cell = ""
        if stats['battery_pct'] is not None:
            battery_pct = stats['battery_pct']
            battery_color = "#4CAF50" if battery_pct > 75 else "#FF9800" if battery_pct > 25 else "#F44336"
            battery_cell = f"""
                <div style="display: flex; align-items: center;">
                    <div style="width: 60px; height: 10px; background: #ddd; border-radius: 5px; margin-right: 8px; overflow: hidden;">
                        <div style="width: {battery_pct}%; height: 100%; background: {battery_color};"></div>
                    </div>
                    <span>{battery_pct:.1f}%</span>
                </div>
            """
        else:
            battery_cell = "N/A"
        
        telemetry_icon = "📊" if stats['has_telemetry'] else "❌"
        routing_icon = "🔗" if stats['has_routing'] else "❌"
        last_seen = stats['last_seen'] or "Unknown"
        
        rows_html.append(f"""
            <tr>
                <td><a href="dashboards.html#{stats['node']}">{stats['node']}</a></td>
                <td>{stats['status']} {stats['status_text']}</td>
                <td>{last_seen}</td>
                <td>{battery_cell}</td>
                <td>{telemetry_icon}</td>
                <td>{routing_icon}</td>
            </tr>
        """)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌐 Meshtastic Network Nodes</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        table {{ width: 100%; border-collapse: collapse; background: white; }}
        th, td {{ padding: 12px; border: 1px solid #ddd; }}
        th {{ background: #2196F3; color: white; }}
    </style>
</head>
<body>
    <h1>🌐 Meshtastic Network Nodes</h1>
    <p>Total: {total_nodes} nodes | Telemetry: {telemetry_nodes} | Routing: {routing_nodes}</p>
    <table>
        <tr>
            <th>Node ID</th>
            <th>Status</th>
            <th>Last Seen</th>
            <th>Battery</th>
            <th>Telemetry</th>
            <th>Routing</th>
        </tr>
        {''.join(rows_html)}
    </table>
</body>
</html>"""

def write_root_index(outdir: Path):
    """Enhanced root index with modern styling and comprehensive navigation using standardized template"""
    
    # Build the content using standardized components
    content = _build_root_index_content(outdir)
    
    # Navigation links (empty since this IS the main page)
    navigation = []
    
    # Use standardized template if available
    if TEMPLATES_AVAILABLE:
        html = get_html_template(
            title="🚀 Meshtastic Network Dashboard", 
            content=content,
            navigation_links=navigation
        )
    else:
        # Fallback HTML
        html = _fallback_root_index_html(outdir, content)
    
    (outdir / "index.html").write_text(html, encoding="utf-8")
    log_info(f"Wrote enhanced root index to {(outdir / 'index.html')}")

def _build_root_index_content(outdir: Path):
    """Build the main content for the root index page."""
    
    # Navigation cards section
    nav_cards = []
    if (outdir / "nodes.html").exists():
        nav_cards.append("""
            <a href="nodes.html" class="metric-card" style="text-decoration: none; color: inherit; display: block; min-height: 120px;">
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 2.5em; margin-bottom: 10px;">🌐</div>
                    <div style="font-weight: bold; margin-bottom: 5px;">All Nodes</div>
                    <div style="font-size: 0.9em; color: #666;">Complete network directory with status indicators</div>
                </div>
            </a>
        """)
    
    if (outdir / "dashboards.html").exists():
        nav_cards.append("""
            <a href="dashboards.html" class="metric-card" style="text-decoration: none; color: inherit; display: block; min-height: 120px;">
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 2.5em; margin-bottom: 10px;">📊</div>
                    <div style="font-weight: bold; margin-bottom: 5px;">Node Dashboards</div>
                    <div style="font-size: 0.9em; color: #666;">Individual telemetry charts for each node</div>
                </div>
            </a>
        """)
    
    if (outdir / "diagnostics.html").exists():
        nav_cards.append("""
            <a href="diagnostics.html" class="metric-card" style="text-decoration: none; color: inherit; display: block; min-height: 120px;">
                <div style="text-align: center; padding: 10px;">
                    <div style="font-size: 2.5em; margin-bottom: 10px;">🔍</div>
                    <div style="font-weight: bold; margin-bottom: 5px;">Diagnostics</div>
                    <div style="font-size: 0.9em; color: #666;">Data quality and merge verification</div>
                </div>
            </a>
        """)
    
    # Network analysis charts section
    chart_items = []
    for name in ["traceroute_hops.png", "traceroute_bottleneck_db.png"]:
        if (outdir / name).exists():
            chart_title = name.replace('_', ' ').replace('.png', '').title()
            chart_items.append(f"""
                <div class="chart-card">
                    <h3>{chart_title}</h3>
                    <a href='{name}'>
                        <img src='{name}' alt='{chart_title}' class="chart-image">
                    </a>
                </div>
            """)
    
    # Topology snapshots section
    topo_imgs = sorted([p.name for p in outdir.glob("topology_*.png")])
    topo_cards = []
    for img in topo_imgs:
        topo_title = img.replace('_', ' ').replace('.png', '').title()
        topo_cards.append(f"""
            <div class="chart-card" style="max-width: 300px;">
                <h3 style="font-size: 1em;">{topo_title}</h3>
                <a href='{img}'>
                    <img src='{img}' alt='{topo_title}' class="chart-image">
                </a>
            </div>
        """)
    
    # Build sections
    content_parts = []
    
    # Navigation section
    if nav_cards:
        content_parts.append(f"""
        <div class="section">
            <h2>🧭 Navigation</h2>
            <div class="metrics-grid">
                {''.join(nav_cards)}
            </div>
        </div>
        """)
    
    # Charts section
    if chart_items:
        content_parts.append(f"""
        <div class="section">
            <h2>📈 Network Analysis Charts</h2>
            <div class="charts-grid">
                {''.join(chart_items)}
            </div>
        </div>
        """)
    
    # Topology section
    if topo_cards:
        content_parts.append(f"""
        <div class="section">
            <h2>🗺️ Network Topology Snapshots</h2>
            <div class="charts-grid">
                {''.join(topo_cards)}
            </div>
        </div>
        """)
    
    # Getting started section if no data yet
    if not (nav_cards or chart_items or topo_cards):
        content_parts.append("""
        <div class="section">
            <h2>🚀 Getting Started</h2>
            <p>Welcome to your Meshtastic network dashboard!</p>
            <p>To get started, collect some telemetry and traceroute data using the logger scripts:</p>
            <ul>
                <li><code>python3 meshtastic_telemetry_logger.py</code> - Collect telemetry data</li>
                <li><code>python3 plot_meshtastic.py --telemetry telemetry.csv --traceroute traceroute.csv --outdir plots</code> - Generate visualizations</li>
            </ul>
            <p>Once you have data, this dashboard will show:</p>
            <ul>
                <li><strong>🌐 All Nodes:</strong> Complete network directory with status indicators</li>
                <li><strong>📊 Node Dashboards:</strong> Individual telemetry charts for each node</li>
                <li><strong>🔍 Diagnostics:</strong> Data quality and merge verification</li>
                <li><strong>📈 Network Charts:</strong> Network-wide analysis and topology</li>
            </ul>
        </div>
        """)
    
    return '\n'.join(content_parts)

def _fallback_root_index_html(outdir: Path, content: str):
    """Fallback HTML for root index if templates are not available."""
    
    # Count available files to show status
    nav_files = len([f for f in ["nodes.html", "dashboards.html", "diagnostics.html"] if (outdir / f).exists()])
    chart_files = len([f for f in ["traceroute_hops.png", "traceroute_bottleneck_db.png"] if (outdir / f).exists()])
    topo_files = len(list(outdir.glob("topology_*.png")))
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Meshtastic Network Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        h1, h2 {{ color: #333; }}
        .nav-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
        .nav-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Meshtastic Network Dashboard</h1>
        <p>Generated: {_now_iso()} • Files: {nav_files} pages, {chart_files} charts, {topo_files} topology snapshots</p>
        {content}
    </div>
</body>
</html>"""

def main():
    args = parse_args()
    base_outdir = Path(args.outdir)
    
    # Handle history preservation
    if args.preserve_history:
        outdir = create_timestamped_output_dir(base_outdir)
        log_info(f"History preservation enabled: {outdir}")
    else:
        outdir = base_outdir
        ensure_outdir(outdir)

    tele = read_merge_telemetry(args.telemetry)
    trace = read_merge_traceroute(args.traceroute)

    diagnostics(tele, trace, outdir, args.telemetry, args.traceroute)

    if not tele.empty:
        plot_per_node_dashboards(tele, outdir, force_regenerate=args.regenerate_charts)
    else:
        log_warn("No telemetry data after merge.")

    if not trace.empty:
        plot_traceroute_timeseries(trace, outdir)
        plot_topology_snapshots(trace, outdir)
    else:
        log_warn("No traceroute data after merge.")

    # Generate comprehensive nodes list
    write_comprehensive_nodes_list(tele, trace, outdir)

    write_root_index(outdir)
    
    if args.preserve_history:
        log_info(f"Outputs in {outdir.resolve()} (latest symlink: {(base_outdir / 'latest').resolve()})")
        log_info(f"Access via: {(base_outdir / 'latest' / 'index.html')}")
    else:
        log_info(f"Outputs in {outdir.resolve()} (open index.html)")

if __name__ == "__main__":
    main()
