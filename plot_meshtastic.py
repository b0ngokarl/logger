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

    # Create a small HTML diagnostics page with summary tables
    html_lines = [
        "<!doctype html>",
        "<meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Diagnostics</title>",
        "<style>body{font-family:Arial,Helvetica,sans-serif;margin:16px}table{border-collapse:collapse;width:100%;max-width:900px}td,th{border:1px solid #ddd;padding:6px}th{background:#f3f3f3;text-align:left}</style>",
        f"<h1>Diagnostics (generated {_now_iso()})</h1>",
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

    (outdir / "diagnostics.html").write_text("\n".join(html_lines), encoding="utf-8")
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
    """Create comprehensive nodes.html with status indicators and statistics"""
    
    # Get unique nodes from both telemetry and traceroute
    tele_nodes = set(tele_df['node'].unique()) if not tele_df.empty else set()
    trace_nodes = set()
    if not trace_df.empty:
        for col in ['source', 'dest']:
            if col in trace_df.columns:
                trace_nodes.update(trace_df[col].unique())
    
    all_nodes = tele_nodes | trace_nodes
    
    # Calculate node statistics
    node_stats = []
    current_time = datetime.now()
    
    for node in sorted(all_nodes):
        stats = {
            'node': node,
            'has_telemetry': node in tele_nodes,
            'has_routing': node in trace_nodes,
            'last_seen': None,
            'battery_pct': None,
            'status': '🔴',  # Default to stale
            'status_text': 'Stale'
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
                elif hours_since < 24:
                    stats['status'] = '🟡'
                    stats['status_text'] = 'Recent'
        
        node_stats.append(stats)
    
    # Generate HTML
    rows_html = []
    for stats in node_stats:
        battery_cell = ""
        if stats['battery_pct'] is not None:
            battery_pct = stats['battery_pct']
            if battery_pct > 75:
                battery_color = "#4CAF50"  # Green
            elif battery_pct > 25:
                battery_color = "#FF9800"  # Orange
            else:
                battery_color = "#F44336"  # Red
            
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
    
    # Calculate summary statistics
    total_nodes = len(all_nodes)
    telemetry_nodes = len(tele_nodes)
    routing_nodes = len(trace_nodes)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🌐 Meshtastic Network Nodes</title>
    <style>
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(45deg, #2196F3, #21CBF3);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #2196F3;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .table-container {{
            padding: 30px;
            overflow-x: auto;
        }}
        
        .search-box {{
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            margin-bottom: 20px;
            transition: border-color 0.3s;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: #2196F3;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        
        th {{
            background: #2196F3;
            color: white;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.3s;
        }}
        
        th:hover {{
            background: #1976D2;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .nav-link {{
            display: inline-block;
            padding: 10px 20px;
            background: #2196F3;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px;
            transition: background 0.3s;
        }}
        
        .nav-link:hover {{
            background: #1976D2;
        }}
        
        .navigation {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Meshtastic Network Nodes</h1>
            <p>Complete network overview • Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="navigation">
            <a href="index.html" class="nav-link">🏠 Main Dashboard</a>
            <a href="dashboards.html" class="nav-link">📊 Node Details</a>
            <a href="diagnostics.html" class="nav-link">🔍 Diagnostics</a>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_nodes}</div>
                <div class="stat-label">Total Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{telemetry_nodes}</div>
                <div class="stat-label">📊 Telemetry Active</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{routing_nodes}</div>
                <div class="stat-label">🔗 Routing Active</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len([s for s in node_stats if s['status'] == '🟢'])}</div>
                <div class="stat-label">🟢 Active Nodes</div>
            </div>
        </div>
        
        <div class="table-container">
            <input type="text" class="search-box" placeholder="🔍 Search nodes..." onkeyup="filterNodes()">
            
            <table id="nodesTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">Node ID</th>
                        <th onclick="sortTable(1)">Status</th>
                        <th onclick="sortTable(2)">Last Seen</th>
                        <th onclick="sortTable(3)">🔋 Battery</th>
                        <th onclick="sortTable(4)">📊 Telemetry</th>
                        <th onclick="sortTable(5)">🔗 Routing</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows_html)}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function filterNodes() {{
            const input = document.querySelector('.search-box');
            const filter = input.value.toUpperCase();
            const table = document.getElementById('nodesTable');
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 1; i < rows.length; i++) {{
                const row = rows[i];
                const nodeId = row.getElementsByTagName('td')[0];
                if (nodeId) {{
                    const txtValue = nodeId.textContent || nodeId.innerText;
                    row.style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
                }}
            }}
        }}
        
        function sortTable(columnIndex) {{
            const table = document.getElementById('nodesTable');
            let rows = Array.from(table.rows).slice(1);
            const isAscending = table.getAttribute('data-sort-direction') !== 'asc';
            
            rows.sort((a, b) => {{
                const aText = a.cells[columnIndex].textContent.trim();
                const bText = b.cells[columnIndex].textContent.trim();
                
                if (columnIndex === 2) {{ // Date column
                    return isAscending ? 
                        new Date(aText) - new Date(bText) : 
                        new Date(bText) - new Date(aText);
                }}
                
                return isAscending ? 
                    aText.localeCompare(bText) : 
                    bText.localeCompare(aText);
            }});
            
            rows.forEach(row => table.appendChild(row));
            table.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
        }}
    </script>
</body>
</html>"""
    
    (outdir / "nodes.html").write_text(html, encoding="utf-8")
    log_info(f"Wrote comprehensive nodes list to {(outdir / 'nodes.html')}")

def write_root_index(outdir: Path):
    # Enhanced root index with modern styling and comprehensive navigation
    chart_items = []
    for name in ["traceroute_hops.png", "traceroute_bottleneck_db.png"]:
        if (outdir / name).exists():
            chart_items.append(f"""
                <div class="chart-card">
                    <h3>{name.replace('_', ' ').replace('.png', '').title()}</h3>
                    <a href='{name}'>
                        <img src='{name}' alt='{name}' class="chart-image">
                    </a>
                </div>
            """)
    
    # Navigation links
    nav_links = []
    if (outdir / "dashboards.html").exists():
        nav_links.append('<a href="dashboards.html" class="nav-card">📊<br>Node Dashboards</a>')
    if (outdir / "diagnostics.html").exists():
        nav_links.append('<a href="diagnostics.html" class="nav-card">🔍<br>Diagnostics</a>')
    if (outdir / "nodes.html").exists():
        nav_links.append('<a href="nodes.html" class="nav-card">🌐<br>All Nodes</a>')
    
    # Topology snapshots
    topo_imgs = sorted([p.name for p in outdir.glob("topology_*.png")])
    topo_cards = []
    for img in topo_imgs:
        topo_cards.append(f"""
            <div class="topo-card">
                <h4>{img.replace('_', ' ').replace('.png', '').title()}</h4>
                <a href='{img}'>
                    <img src='{img}' alt='{img}' class="topo-image">
                </a>
            </div>
        """)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Meshtastic Network Dashboard</title>
    <style>
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        
        .header {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 30px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 3em;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .header p {{
            color: #666;
            font-size: 1.1em;
            margin: 10px 0 0 0;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px;
        }}
        
        .nav-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .nav-card {{
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            text-decoration: none;
            color: #333;
            font-weight: 500;
            font-size: 1.1em;
            transition: all 0.3s ease;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        
        .nav-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
            background: white;
        }}
        
        .section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }}
        
        .section h2 {{
            margin-top: 0;
            color: #333;
            font-size: 1.8em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .chart-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        
        .chart-card h3 {{
            margin-top: 0;
            color: #333;
        }}
        
        .chart-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }}
        
        .chart-image:hover {{
            transform: scale(1.02);
        }}
        
        .topo-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .topo-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }}
        
        .topo-card h4 {{
            margin-top: 0;
            color: #333;
            font-size: 0.9em;
        }}
        
        .topo-image {{
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2em;
            }}
            .container {{
                padding: 15px;
            }}
            .nav-card {{
                padding: 20px;
                font-size: 1em;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Meshtastic Network Dashboard</h1>
        <p>Network Analysis & Monitoring • Generated: {_now_iso()}</p>
    </div>
    
    <div class="container">
        <div class="nav-grid">
            {''.join(nav_links)}
        </div>
        
        {f'''
        <div class="section">
            <h2>📈 Network Analysis Charts</h2>
            <div class="charts-grid">
                {''.join(chart_items)}
            </div>
        </div>
        ''' if chart_items else ''}
        
        {f'''
        <div class="section">
            <h2>🗺️ Network Topology Snapshots</h2>
            <div class="topo-grid">
                {''.join(topo_cards)}
            </div>
        </div>
        ''' if topo_cards else ''}
        
        {f'''
        <div class="section">
            <h2>ℹ️ Getting Started</h2>
            <p>Welcome to your Meshtastic network dashboard! Use the navigation cards above to explore:</p>
            <ul>
                <li><strong>📊 Node Dashboards:</strong> Individual telemetry charts for each node</li>
                <li><strong>🔍 Diagnostics:</strong> Data quality and merge verification</li>
                <li><strong>🌐 All Nodes:</strong> Complete network directory with status indicators</li>
            </ul>
        </div>
        ''' if not (chart_items or topo_cards) else ''}
    </div>
    
    <div class="footer">
        <p>Meshtastic Logger v3.0 • Enhanced dashboards with history preservation</p>
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
