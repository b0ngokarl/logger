#!/usr/bin/env python3
"""
Plot Meshtastic telemetry & traceroute CSVs
- Merges multiple CSV inputs (e.g., mix of --once and --interval runs)
- De-duplicates rows, sorts by time
- Per-node dashboards, traceroute time-series, topology snapshots
- Diagnostics to verify merged ranges
- Matplotlib only (no seaborn), single-plot figures

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
from datetime import datetime

def ensure_outdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def parse_args():
    ap = argparse.ArgumentParser(description="Plot Meshtastic telemetry & traceroute CSVs (v3, merge-aware)")
    ap.add_argument("--telemetry", nargs="+", required=True, help="One or more telemetry CSVs")
    ap.add_argument("--traceroute", nargs="+", required=True, help="One or more traceroute CSVs")
    ap.add_argument("--outdir", default="plots", help="Output directory for PNGs and HTML")
    ap.add_argument("--regenerate-charts", action="store_true", help="Force regeneration of all charts")
    ap.add_argument("--preserve-history", action="store_true", help="Create timestamped subdirectory to preserve history")
    return ap.parse_args()

def create_timestamped_output_dir(base_outdir: Path, preserve_history: bool = False):
    """Create output directory with optional timestamp for history preservation."""
    if not preserve_history:
        return base_outdir
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped_dir = base_outdir / f"run_{timestamp}"
    
    # Also create a "latest" symlink for easy access
    latest_link = base_outdir / "latest"
    
    return timestamped_dir, latest_link

def read_merge_telemetry(paths):
    need = ["timestamp","node","battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s"]
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
    for col in ["battery_pct","voltage_v","channel_util_pct","air_tx_pct","uptime_s"]:
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

    # Create an enhanced HTML diagnostics page with better styling and organization
    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        line-height: 1.6;
        color: #333;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        padding: 20px;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        overflow: hidden;
    }
    .header {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 30px;
        text-align: center;
    }
    .header h1 {
        font-size: 2.2em;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    .content {
        padding: 30px;
    }
    .section {
        margin-bottom: 40px;
        background: #f8f9fa;
        border-radius: 12px;
        padding: 25px;
        border-left: 5px solid #4facfe;
    }
    .section h2 {
        color: #495057;
        margin-bottom: 20px;
        font-size: 1.5em;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        margin-top: 15px;
    }
    th, td {
        padding: 15px;
        text-align: left;
        border-bottom: 1px solid #e9ecef;
    }
    th {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.9em;
        letter-spacing: 0.5px;
    }
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    tr:hover {
        background-color: #e7f3ff;
        transform: scale(1.01);
        transition: all 0.2s ease;
    }
    .sources ul {
        list-style: none;
        display: grid;
        gap: 10px;
        margin-top: 15px;
    }
    .sources li {
        background: white;
        padding: 12px 18px;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    .stat-badge {
        background: linear-gradient(135deg, #28a745, #20c997);
        color: white;
        padding: 6px 12px;
        border-radius: 15px;
        font-size: 0.8em;
        font-weight: 500;
    }
    .back-link {
        text-align: center;
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #dee2e6;
    }
    .back-link a {
        color: #4facfe;
        text-decoration: none;
        padding: 12px 25px;
        border: 2px solid #4facfe;
        border-radius: 25px;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    .back-link a:hover {
        background: #4facfe;
        color: white;
        transform: translateY(-2px);
    }
    @media (max-width: 768px) {
        .container { margin: 10px; }
        .header { padding: 20px; }
        .content { padding: 20px; }
        .section { padding: 20px; }
        th, td { padding: 10px; }
    }
    """
    
    html_content = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Network Diagnostics</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Network Diagnostics</h1>
            <div>Generated: {_now_iso()}</div>
        </div>
        
        <div class="content">
            <div class="section sources">
                <h2>📂 Data Sources</h2>
                <ul>"""
    
    for s in sources_tele:
        html_content += f"<li>📊 Telemetry: <strong>{s}</strong></li>"
    for s in sources_trace:
        html_content += f"<li>🗺️ Traceroute: <strong>{s}</strong></li>"
    
    html_content += "</ul></div>"

    if len(df_tele):
        total_tele_rows = len(df_tele)
        unique_nodes = df_tele['node'].nunique()
        html_content += f"""
            <div class="section">
                <h2>📊 Telemetry Summary <span class="stat-badge">{unique_nodes} nodes, {total_tele_rows} records</span></h2>
                <table>
                    <tr>
                        <th>Node ID</th>
                        <th>Last Seen</th>
                        <th>Records</th>
                        <th>Battery %</th>
                        <th>Voltage V</th>
                        <th>Est. Runtime</th>
                    </tr>"""
        
        for node, part in df_tele.groupby("node"):
            last = part["timestamp"].max()
            rows = len(part)
            latest_batt = part.sort_values("timestamp").iloc[-1]["battery_pct"] if rows else ""
            latest_volt = part.sort_values("timestamp").iloc[-1]["voltage_v"] if rows else ""
            latest_runtime = est_runtimes.get(node, "N/A")
            
            # Color-code battery levels
            batt_color = "🟢" if latest_batt and latest_batt > 70 else "🟡" if latest_batt and latest_batt > 30 else "🔴" if latest_batt else "⚫"
            
            html_content += f"""
                    <tr>
                        <td><strong>{node}</strong></td>
                        <td>{_fmt_ts(last)}</td>
                        <td>{rows}</td>
                        <td>{batt_color} {latest_batt}%</td>
                        <td>{latest_volt}V</td>
                        <td>{latest_runtime}</td>
                    </tr>"""
        
        html_content += "</table></div>"

    if len(df_trace):
        total_trace_rows = len(df_trace)
        unique_routes = df_trace.groupby(['dest', 'direction']).ngroups
        html_content += f"""
            <div class="section">
                <h2>🗺️ Traceroute Summary <span class="stat-badge">{unique_routes} routes, {total_trace_rows} records</span></h2>
                <table>
                    <tr>
                        <th>Destination</th>
                        <th>Direction</th>
                        <th>Last Seen</th>
                        <th>Records</th>
                        <th>Status</th>
                    </tr>"""
        
        for (dest, direction), part in df_trace.groupby(["dest", "direction"]):
            last = part["timestamp"].max()
            rows = len(part)
            
            # Calculate time since last trace
            from datetime import datetime
            try:
                last_dt = pd.to_datetime(last)
                now_dt = datetime.now(last_dt.tz)
                hours_ago = (now_dt - last_dt).total_seconds() / 3600
                status = "🟢 Active" if hours_ago < 1 else "🟡 Recent" if hours_ago < 24 else "🔴 Stale"
            except:
                status = "❓ Unknown"
                
            html_content += f"""
                    <tr>
                        <td><strong>{dest}</strong></td>
                        <td>{direction}</td>
                        <td>{_fmt_ts(last)}</td>
                        <td>{rows}</td>
                        <td>{status}</td>
                    </tr>"""
        
        html_content += "</table></div>"
    
    html_content += """
            <div class="back-link">
                <a href="index.html">← Back to Dashboard</a>
            </div>
        </div>
    </div>
</body>
</html>"""

    (outdir / "diagnostics.html").write_text(html_content, encoding="utf-8")
    log_info(f"Wrote diagnostics HTML to {(outdir / 'diagnostics.html')}")

def plot_per_node_dashboards(df: pd.DataFrame, outdir: Path, force_regenerate=False):
    metrics = [
        ("battery_pct", "Battery (%)", "battery"),
        ("voltage_v", "Voltage (V)", "voltage"),
        ("channel_util_pct", "Channel Utilization (%)", "channel_util"),
        ("air_tx_pct", "Air TX Utilization (%)", "air_tx"),
        ("uptime_s", "Uptime (hours)", "uptime_hours"),
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

            # Build an enhanced responsive HTML per-node page with comprehensive information
            latest = part.sort_values("timestamp").iloc[-1]
            last_seen = _fmt_ts(latest["timestamp"])
            latest_batt = latest.get("battery_pct", "N/A")
            latest_volt = latest.get("voltage_v", "N/A")
            latest_chan_util = latest.get("channel_util_pct", "N/A")
            latest_air_tx = latest.get("air_tx_pct", "N/A")
            latest_uptime = latest.get("uptime_s", "N/A")
            
            # Format uptime nicely
            if latest_uptime != "N/A" and latest_uptime:
                uptime_hours = latest_uptime / 3600
                if uptime_hours < 24:
                    uptime_display = f"{uptime_hours:.1f} hours"
                else:
                    uptime_display = f"{uptime_hours/24:.1f} days"
            else:
                uptime_display = "N/A"

            # Enhanced CSS for individual node pages
            css = """
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
                backdrop-filter: blur(10px);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 15px;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }
            .stats-bar {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .stat-card {
                background: rgba(255, 255, 255, 0.2);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                backdrop-filter: blur(10px);
            }
            .stat-value {
                font-size: 1.5em;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .stat-label {
                font-size: 0.9em;
                opacity: 0.9;
            }
            .content {
                padding: 30px;
            }
            .charts-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 25px;
                margin: 25px 0;
            }
            .chart-card {
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border: 1px solid #e9ecef;
            }
            .chart-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15);
            }
            .chart-card h3 {
                color: #495057;
                margin-bottom: 15px;
                font-size: 1.2em;
                padding-bottom: 10px;
                border-bottom: 2px solid #e9ecef;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .chart-link {
                display: block;
                text-decoration: none;
                border-radius: 8px;
                overflow: hidden;
                transition: transform 0.2s ease;
            }
            .chart-link:hover {
                transform: scale(1.02);
            }
            .chart-link img {
                width: 100%;
                height: auto;
                display: block;
                border-radius: 8px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }
            .info-section {
                background: #f8f9fa;
                border-radius: 12px;
                padding: 25px;
                margin: 25px 0;
                border-left: 5px solid #4facfe;
            }
            .info-section h3 {
                color: #495057;
                margin-bottom: 15px;
            }
            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
            }
            .info-item {
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            .info-label {
                font-weight: 600;
                color: #6c757d;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 5px;
            }
            .info-value {
                font-size: 1.1em;
                color: #495057;
                font-weight: 500;
            }
            .back-link {
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #dee2e6;
            }
            .back-link a {
                color: #4facfe;
                text-decoration: none;
                padding: 12px 25px;
                border: 2px solid #4facfe;
                border-radius: 25px;
                transition: all 0.3s ease;
                font-weight: 500;
                display: inline-block;
            }
            .back-link a:hover {
                background: #4facfe;
                color: white;
                transform: translateY(-2px);
            }
            @media (max-width: 768px) {
                .container { margin: 10px; }
                .header { padding: 20px; }
                .content { padding: 20px; }
                .charts-grid { grid-template-columns: 1fr; }
                .stats-bar { grid-template-columns: repeat(2, 1fr); }
            }
            """
            
            # Chart icons mapping
            chart_icons = {
                "battery": "🔋",
                "voltage": "⚡",
                "channel_util": "📊", 
                "air_tx": "📡",
                "uptime_hours": "⏱️"
            }
            
            html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Node {node} Dashboard</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📡 Node {node}</h1>
            <div class="stats-bar">
                <div class="stat-card">
                    <div class="stat-value">{latest_batt}%</div>
                    <div class="stat-label">🔋 Battery</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{latest_volt}V</div>
                    <div class="stat-label">⚡ Voltage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{latest_chan_util}%</div>
                    <div class="stat-label">📊 Channel Usage</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{uptime_display}</div>
                    <div class="stat-label">⏱️ Uptime</div>
                </div>
            </div>
        </div>
        
        <div class="content">
            <div class="info-section">
                <h3>📋 Node Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Last Seen</div>
                        <div class="info-value">{last_seen}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Air TX Usage</div>
                        <div class="info-value">{latest_air_tx}%</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Records Count</div>
                        <div class="info-value">{len(part)}</div>
                    </div>
                    {f'<div class="info-item"><div class="info-label">Est. Runtime</div><div class="info-value">{est_runtime.replace(" &nbsp;|&nbsp; Est. runtime: ", "")}</div></div>' if est_runtime else ''}
                </div>
            </div>
            
            <div class="charts-grid">"""
            
            for img in imgs:
                chart_key = img.replace(".png", "")
                icon = chart_icons.get(chart_key, "📈")
                title = img.replace(".png", "").replace("_", " ").title()
                html += f"""
                <div class="chart-card">
                    <h3>{icon} {title}</h3>
                    <a href='{img}' class="chart-link">
                        <img src='{img}' alt='{img}'>
                    </a>
                </div>"""
            
            html += """
            </div>
            
            <div class="back-link">
                <a href='../index.html'>← Back to Dashboard</a>
            </div>
        </div>
    </div>
</body>
</html>"""
            
            (node_dir / "index.html").write_text(html, encoding="utf-8")
            dashboards[node] = node_dir
    if dashboards:
        # Generate enhanced dashboards overview page
        css = """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        .header {
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            color: #333;
            padding: 30px;
            text-align: center;
            border-radius: 15px 15px 0 0;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        }
        .content {
            padding: 30px;
        }
        .nodes-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin: 25px 0;
        }
        .node-card {
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            border: 1px solid #e9ecef;
            position: relative;
            overflow: hidden;
        }
        .node-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        .node-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
        }
        .node-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        .node-icon {
            font-size: 2em;
            margin-right: 15px;
        }
        .node-title {
            font-size: 1.4em;
            font-weight: 600;
            color: #495057;
        }
        .node-link {
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .back-link {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
        }
        .back-link a {
            color: #4facfe;
            text-decoration: none;
            padding: 12px 25px;
            border: 2px solid #4facfe;
            border-radius: 25px;
            transition: all 0.3s ease;
            font-weight: 500;
            display: inline-block;
        }
        .back-link a:hover {
            background: #4facfe;
            color: white;
            transform: translateY(-2px);
        }
        @media (max-width: 768px) {
            .container { margin: 10px; }
            .header { padding: 20px; }
            .content { padding: 20px; }
            .nodes-grid { grid-template-columns: 1fr; }
        }
        """
        
        html_content = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Node Dashboards</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Node Dashboards</h1>
            <div>Individual monitoring dashboards for each network node</div>
        </div>
        
        <div class="content">
            <div class="nodes-grid">"""
        
        for node, p in dashboards.items():
            rel = p.name + "/index.html"
            html_content += f"""
                <div class="node-card">
                    <a href='{rel}' class="node-link">
                        <div class="node-header">
                            <div class="node-icon">📡</div>
                            <div class="node-title">Node {node}</div>
                        </div>
                        <div>Click to view detailed telemetry data, charts, and analysis</div>
                    </a>
                </div>"""
        
        html_content += """
            </div>
            
            <div class="back-link">
                <a href="index.html">← Back to Main Dashboard</a>
            </div>
        </div>
    </div>
</body>
</html>"""
        
        (outdir / "dashboards.html").write_text(html_content, encoding="utf-8")
        
        # Also generate comprehensive nodes list
        write_comprehensive_nodes_list(outdir, dashboards)

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

def write_comprehensive_nodes_list(outdir: Path, dashboards: dict = None):
    """Create a comprehensive nodes list with detailed information."""
    
    # Try to read telemetry and traceroute data to get node information
    tele_files = list(outdir.glob("*telemetry*.csv"))
    trace_files = list(outdir.glob("*traceroute*.csv"))
    
    nodes_info = {}
    
    # Collect info from CSV files if they exist in the same directory
    if not tele_files:
        # Look for CSV files in parent directory or current directory
        tele_files = list(Path(".").glob("*telemetry*.csv")) + list(Path("..").glob("*telemetry*.csv"))
    if not trace_files:
        trace_files = list(Path(".").glob("*traceroute*.csv")) + list(Path("..").glob("*traceroute*.csv"))
    
    # Collect telemetry data
    for tele_file in tele_files[:3]:  # Limit to first 3 files to avoid processing too much
        try:
            df = pd.read_csv(tele_file)
            for node, group in df.groupby("node"):
                if node not in nodes_info:
                    nodes_info[node] = {"type": "telemetry", "records": 0, "last_seen": None, "battery": None, "voltage": None}
                nodes_info[node]["records"] += len(group)
                latest = group.sort_values("timestamp").iloc[-1]
                nodes_info[node]["last_seen"] = latest["timestamp"]
                nodes_info[node]["battery"] = latest.get("battery_pct", "N/A")
                nodes_info[node]["voltage"] = latest.get("voltage_v", "N/A")
        except Exception as e:
            print(f"[DEBUG] Could not process {tele_file}: {e}")
    
    # Collect traceroute data
    for trace_file in trace_files[:3]:  # Limit to first 3 files
        try:
            df = pd.read_csv(trace_file)
            for dest in df["dest"].unique():
                if dest not in nodes_info:
                    nodes_info[dest] = {"type": "traceroute", "records": 0, "last_seen": None}
                dest_data = df[df["dest"] == dest]
                nodes_info[dest]["records"] += len(dest_data)
                if nodes_info[dest]["last_seen"] is None:
                    nodes_info[dest]["last_seen"] = dest_data["timestamp"].max()
            
            # Also collect "from" and "to" nodes
            for col in ["from", "to"]:
                for node in df[col].dropna().unique():
                    if node not in nodes_info:
                        nodes_info[node] = {"type": "routing", "records": 0, "last_seen": None}
        except Exception as e:
            print(f"[DEBUG] Could not process {trace_file}: {e}")
    
    # Add dashboard info
    if dashboards:
        for node in dashboards.keys():
            if node not in nodes_info:
                nodes_info[node] = {"type": "dashboard", "records": 0, "last_seen": None}
    
    # Enhanced CSS for nodes list
    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        line-height: 1.6;
        color: #333;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        padding: 20px;
    }
    .container {
        max-width: 1400px;
        margin: 0 auto;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }
    .header {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        color: #333;
        padding: 30px;
        text-align: center;
        border-radius: 15px 15px 0 0;
    }
    .header h1 {
        font-size: 2.5em;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
    }
    .stats-summary {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin: 20px 0;
    }
    .stat-card {
        background: rgba(255, 255, 255, 0.8);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stat-number {
        font-size: 2em;
        font-weight: bold;
        color: #4facfe;
    }
    .stat-label {
        font-size: 0.9em;
        color: #666;
        margin-top: 5px;
    }
    .content {
        padding: 30px;
    }
    .nodes-table {
        width: 100%;
        border-collapse: collapse;
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        margin: 25px 0;
    }
    .nodes-table th {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 20px;
        text-align: left;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.9em;
        letter-spacing: 0.5px;
    }
    .nodes-table td {
        padding: 18px 20px;
        border-bottom: 1px solid #e9ecef;
    }
    .nodes-table tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    .nodes-table tr:hover {
        background-color: #e7f3ff;
        transform: scale(1.01);
        transition: all 0.2s ease;
    }
    .node-id {
        font-weight: 600;
        color: #495057;
        font-size: 1.1em;
    }
    .node-type {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 15px;
        font-size: 0.8em;
        font-weight: 500;
        text-transform: uppercase;
    }
    .type-telemetry {
        background: #d1ecf1;
        color: #0c5460;
    }
    .type-traceroute {
        background: #f8d7da;
        color: #721c24;
    }
    .type-routing {
        background: #d4edda;
        color: #155724;
    }
    .type-dashboard {
        background: #fff3cd;
        color: #856404;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-active {
        background: #28a745;
    }
    .status-recent {
        background: #ffc107;
    }
    .status-stale {
        background: #dc3545;
    }
    .status-unknown {
        background: #6c757d;
    }
    .dashboard-link {
        color: #4facfe;
        text-decoration: none;
        padding: 6px 12px;
        border: 1px solid #4facfe;
        border-radius: 15px;
        font-size: 0.9em;
        transition: all 0.2s ease;
    }
    .dashboard-link:hover {
        background: #4facfe;
        color: white;
    }
    .back-link {
        text-align: center;
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #dee2e6;
    }
    .back-link a {
        color: #4facfe;
        text-decoration: none;
        padding: 12px 25px;
        border: 2px solid #4facfe;
        border-radius: 25px;
        transition: all 0.3s ease;
        font-weight: 500;
        display: inline-block;
    }
    .back-link a:hover {
        background: #4facfe;
        color: white;
        transform: translateY(-2px);
    }
    @media (max-width: 768px) {
        .container { margin: 10px; }
        .header { padding: 20px; }
        .content { padding: 20px; }
        .stats-summary { grid-template-columns: repeat(2, 1fr); }
        .nodes-table th, .nodes-table td { padding: 12px; }
    }
    """
    
    # Calculate statistics
    total_nodes = len(nodes_info)
    telemetry_nodes = len([n for n in nodes_info.values() if n.get("battery") is not None])
    routing_nodes = len([n for n in nodes_info.values() if n["type"] in ["routing", "traceroute"]])
    active_dashboards = len(dashboards) if dashboards else 0
    
    html_content = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>All Nodes</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Network Nodes Directory</h1>
            <div>Complete list of all discovered and monitored nodes</div>
            
            <div class="stats-summary">
                <div class="stat-card">
                    <div class="stat-number">{total_nodes}</div>
                    <div class="stat-label">Total Nodes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{telemetry_nodes}</div>
                    <div class="stat-label">With Telemetry</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{routing_nodes}</div>
                    <div class="stat-label">In Routes</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{active_dashboards}</div>
                    <div class="stat-label">Active Dashboards</div>
                </div>
            </div>
        </div>
        
        <div class="content">
            <table class="nodes-table">
                <thead>
                    <tr>
                        <th>Node ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Last Seen</th>
                        <th>Records</th>
                        <th>Battery</th>
                        <th>Voltage</th>
                        <th>Dashboard</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Sort nodes by ID for consistent display
    for node_id in sorted(nodes_info.keys()):
        info = nodes_info[node_id]
        
        # Determine status based on last seen
        status_class = "status-unknown"
        status_text = "Unknown"
        
        if info["last_seen"]:
            try:
                from datetime import datetime
                last_dt = pd.to_datetime(info["last_seen"])
                now_dt = datetime.now(last_dt.tz) if last_dt.tz else datetime.now()
                hours_ago = (now_dt - last_dt).total_seconds() / 3600
                
                if hours_ago < 1:
                    status_class = "status-active"
                    status_text = "Active"
                elif hours_ago < 24:
                    status_class = "status-recent"  
                    status_text = "Recent"
                else:
                    status_class = "status-stale"
                    status_text = "Stale"
            except:
                pass
        
        # Format last seen
        last_seen_display = "Never"
        if info["last_seen"]:
            try:
                last_seen_display = _fmt_ts(info["last_seen"])
            except:
                last_seen_display = str(info["last_seen"])[:19]  # Truncate to basic format
        
        # Dashboard link
        dashboard_link = ""
        if dashboards and node_id in dashboards:
            dashboard_path = dashboards[node_id].name + "/index.html"
            dashboard_link = f'<a href="{dashboard_path}" class="dashboard-link">View</a>'
        
        # Node type styling
        node_type = info["type"]
        type_class = f"type-{node_type}"
        
        html_content += f"""
                    <tr>
                        <td class="node-id">{node_id}</td>
                        <td><span class="node-type {type_class}">{node_type}</span></td>
                        <td><span class="status-indicator {status_class}"></span>{status_text}</td>
                        <td>{last_seen_display}</td>
                        <td>{info["records"]}</td>
                        <td>{info.get("battery", "N/A")}</td>
                        <td>{info.get("voltage", "N/A")}</td>
                        <td>{dashboard_link}</td>
                    </tr>"""
    
    html_content += """
                </tbody>
            </table>
            
            <div class="back-link">
                <a href="index.html">← Back to Main Dashboard</a>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    (outdir / "nodes.html").write_text(html_content, encoding="utf-8")
    log_info(f"Wrote comprehensive nodes list to {(outdir / 'nodes.html')}")

def write_root_index(outdir: Path):
    """Generate an enhanced root index.html with improved styling and organization."""
    # Collect available content
    items = []
    for name in ["traceroute_hops.png", "traceroute_bottleneck_db.png"]:
        if (outdir / name).exists():
            title = name.replace("traceroute_", "").replace("_", " ").replace(".png", "").title()
            items.append(f"<div class='chart-card'><h3>{title}</h3><a href='{name}' class='chart-link'><img src='{name}' alt='{name}'></a></div>")
    
    # Navigation links
    links = []
    if (outdir / "dashboards.html").exists():
        links.append("<li><a href='dashboards.html' class='nav-link'>📊 Per-Node Dashboards</a></li>")
    if (outdir / "diagnostics.html").exists():
        links.append("<li><a href='diagnostics.html' class='nav-link'>🔍 Diagnostics</a></li>")
    if (outdir / "nodes.html").exists():
        links.append("<li><a href='nodes.html' class='nav-link'>📋 All Nodes</a></li>")
    
    # Topology snapshots
    topo_imgs = sorted([p.name for p in outdir.glob("topology_*.png")])
    topo_html = ""
    if topo_imgs:
        topo_cards = []
        for img in topo_imgs:
            title = img.replace("topology_", "").replace("_", " ").replace(".png", "").title()
            topo_cards.append(f"<div class='chart-card'><h4>{title}</h4><a href='{img}' class='chart-link'><img src='{img}' alt='{img}'></a></div>")
        topo_html = f"<div class='chart-grid'>{''.join(topo_cards)}</div>"
    
    # Enhanced CSS with modern styling
    css = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        line-height: 1.6;
        color: #333;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
    }
    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        margin-top: 20px;
        margin-bottom: 20px;
    }
    header {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 30px;
        text-align: center;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    header h1 {
        font-size: 2.5em;
        margin-bottom: 10px;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    .subtitle {
        font-size: 1.1em;
        opacity: 0.9;
        font-weight: 300;
    }
    nav {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 30px;
        border-left: 5px solid #4facfe;
    }
    nav ul {
        list-style: none;
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
    }
    .nav-link {
        text-decoration: none;
        color: #495057;
        padding: 12px 20px;
        border-radius: 8px;
        background: white;
        border: 1px solid #dee2e6;
        transition: all 0.3s ease;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .nav-link:hover {
        background: #4facfe;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(79, 172, 254, 0.3);
    }
    .chart-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
        gap: 25px;
        margin: 25px 0;
    }
    .chart-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid #e9ecef;
    }
    .chart-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15);
    }
    .chart-card h3, .chart-card h4 {
        color: #495057;
        margin-bottom: 15px;
        font-size: 1.3em;
        border-bottom: 2px solid #e9ecef;
        padding-bottom: 8px;
    }
    .chart-link {
        display: block;
        text-decoration: none;
        border-radius: 8px;
        overflow: hidden;
        transition: transform 0.2s ease;
    }
    .chart-link:hover {
        transform: scale(1.02);
    }
    .chart-link img {
        width: 100%;
        height: auto;
        display: block;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .section-header {
        font-size: 1.8em;
        color: #495057;
        margin: 40px 0 20px 0;
        padding-bottom: 10px;
        border-bottom: 3px solid #4facfe;
        text-align: center;
    }
    .info-badge {
        background: #e7f3ff;
        color: #0066cc;
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: 500;
        display: inline-block;
        margin: 10px 5px;
        border: 1px solid #b3d9ff;
    }
    @media (max-width: 768px) {
        .container { padding: 15px; margin: 10px; }
        header { padding: 20px; }
        header h1 { font-size: 2em; }
        nav ul { flex-direction: column; }
        .chart-grid { grid-template-columns: 1fr; }
    }
    """
    
    html = f"""<!doctype html>
<html lang="en">
<head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Meshtastic Network Dashboard</title>
    <style>{css}</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌐 Meshtastic Network Dashboard</h1>
            <div class="subtitle">Network Monitoring & Analysis Portal</div>
            <div class="info-badge">Generated: {_now_iso()}</div>
        </header>
        
        <nav>
            <ul>{''.join(links)}</ul>
        </nav>
        
        <main>
            {f'<div class="section-header">📈 Network Overview</div><div class="chart-grid">{"".join(items)}</div>' if items else ''}
            
            {f'<div class="section-header">🗺️ Network Topology</div>{topo_html}' if topo_html else ''}
            
            {f'<div class="section-header">ℹ️ Additional Information</div><p style="text-align: center; color: #6c757d; margin: 20px 0;">Use the navigation links above to explore detailed node information, diagnostics, and more network insights.</p>' if not items and not topo_html else ''}
        </main>
    </div>
</body>
</html>"""
    
    (outdir / "index.html").write_text(html, encoding="utf-8")
    log_info(f"Wrote enhanced root index to {(outdir / 'index.html')}")

def main():
    args = parse_args()
    base_outdir = Path(args.outdir)
    
    # Handle history preservation
    if args.preserve_history:
        outdir, latest_link = create_timestamped_output_dir(base_outdir, True)
        ensure_outdir(outdir)
        
        # Create/update the latest symlink
        if latest_link.is_symlink():
            latest_link.unlink()
        if not latest_link.exists():
            try:
                import os
                os.symlink(outdir.name, latest_link)
                log_info(f"Created 'latest' symlink pointing to {outdir.name}")
            except OSError:
                # Symlinks might not work on all systems, just copy the path info
                (base_outdir / "latest.txt").write_text(str(outdir.name))
                log_info(f"Created latest.txt with path: {outdir.name}")
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

    write_root_index(outdir)
    
    if args.preserve_history:
        log_info(f"History preserved in timestamped directory: {outdir}")
        log_info(f"Current output available at: {outdir.resolve()}")
        if (base_outdir / "latest.txt").exists():
            log_info(f"Latest run info: {(base_outdir / 'latest.txt').read_text().strip()}")
    
    log_info(f"Outputs in {outdir.resolve()} (open index.html)")

if __name__ == "__main__":
    main()
