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
        html_lines.append("<tr><th>Node</th><th>Last seen</th><th>Rows</th><th>Latest battery</th><th>Latest voltage</th></tr>")
        for node, part in df_tele.groupby("node"):
            last = part["timestamp"].max()
            rows = len(part)
            latest_batt = part.sort_values("timestamp").iloc[-1]["battery_pct"] if rows else ""
            latest_volt = part.sort_values("timestamp").iloc[-1]["voltage_v"] if rows else ""
            html_lines.append(f"<tr><td>{node}</td><td>{_fmt_ts(last)}</td><td>{rows}</td><td>{latest_batt}</td><td>{latest_volt}</td></tr>")
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

def plot_per_node_dashboards(df: pd.DataFrame, outdir: Path):
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
            plt.figure()
            plt.plot(x, y)
            plt.xlabel("Time")
            plt.ylabel(ylabel)
            plt.title(f"{node} - {ylabel}")
            plt.tight_layout()
            fname = node_dir / f"{slug}.png"
            plt.savefig(fname)
            plt.close()
            imgs.append(fname.name)
        if imgs:
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
                f"<p>Last seen: {last_seen} &nbsp;|&nbsp; Battery: {latest_batt} &nbsp;|&nbsp; Voltage: {latest_volt}</p>",
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

def write_root_index(outdir: Path):
    # Make the root index responsive and link diagnostics
    items = []
    for name in ["traceroute_hops.png", "traceroute_bottleneck_db.png"]:
        if (outdir / name).exists():
            items.append(f"<section><h3>{name}</h3><a href='{name}'><img src='{name}' alt='{name}' style='max-width:100%;height:auto;border:1px solid #ddd;padding:4px;background:#fff'></a></section>")
    links = []
    if (outdir / "dashboards.html").exists():
        links.append("<li><a href='dashboards.html'>Per-Node Dashboards</a></li>")
    if (outdir / "diagnostics.html").exists():
        links.append("<li><a href='diagnostics.html'>Diagnostics</a></li>")
    topo_imgs = sorted([p.name for p in outdir.glob("topology_*.png")])
    topo_html = "".join(f"<p><a href='{n}'><img src='{n}' alt='{n}' style='max-width:100%;height:auto;border:1px solid #ddd;padding:4px;background:#fff'></a></p>" for n in topo_imgs)
    html = f"""<!doctype html>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Meshtastic Plots</title>
<style>body{{font-family:Arial,Helvetica,sans-serif;margin:12px}}header{{display:flex;align-items:center;justify-content:space-between}}main{{max-width:1100px;margin-top:12px}}</style>
<header><h1>Meshtastic Plots</h1><div>Generated: {_now_iso()}</div></header>
<nav><ul>{''.join(links)}</ul></nav>
<main>
{''.join(items)}
<h2>Topology Snapshots</h2>
{topo_html}
</main>
"""
    (outdir / "index.html").write_text(html, encoding="utf-8")
    log_info(f"Wrote root index to {(outdir / 'index.html')}")

def main():
    args = parse_args()
    outdir = Path(args.outdir)
    ensure_outdir(outdir)

    tele = read_merge_telemetry(args.telemetry)
    trace = read_merge_traceroute(args.traceroute)

    diagnostics(tele, trace, outdir, args.telemetry, args.traceroute)

    if not tele.empty:
        plot_per_node_dashboards(tele, outdir)
    else:
        log_warn("No telemetry data after merge.")

    if not trace.empty:
        plot_traceroute_timeseries(trace, outdir)
        plot_topology_snapshots(trace, outdir)
    else:
        log_warn("No traceroute data after merge.")

    write_root_index(outdir)
    log_info(f"Outputs in {outdir.resolve()} (open index.html)")

if __name__ == "__main__":
    main()
