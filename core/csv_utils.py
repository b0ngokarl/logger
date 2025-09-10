#!/usr/bin/env python3
"""
CSV utilities for handling telemetry and traceroute data.
"""
import time
from pathlib import Path
from typing import List, Any


def iso_now() -> str:
    """Return the current time as an ISO 8601 formatted string."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def ensure_header(csv_path: Path, header: List[str]) -> None:
    """
    Ensure the CSV file at csv_path has the given header row.
    If the file doesn't exist or doesn't have the correct header, add it.
    
    Args:
        csv_path: Path to CSV file
        header: List of column names for header
    """
    header_line = ",".join(header)
    
    if not csv_path.exists():
        with csv_path.open("w", encoding="utf-8") as f:
            f.write(header_line + "\n")
        return
    
    # Read existing content
    with csv_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Check if first line is the correct header
    if not lines or lines[0].strip() != header_line:
        # Write correct header and preserve existing data (skip old header if present)
        with csv_path.open("w", encoding="utf-8") as f:
            f.write(header_line + "\n")
            # Skip first line if it looks like a header (contains column names)
            start_idx = 1 if lines and any(col in lines[0] for col in header[:3]) else 0
            for line in lines[start_idx:]:
                if line.strip() and not line.startswith(header_line):
                    f.write(line)


def append_row(csv_path: Path, row: List[Any]) -> None:
    """
    Append a row to the CSV file at csv_path.
    
    Args:
        csv_path: Path to CSV file
        row: List of values to append
    """
    with csv_path.open("a", encoding="utf-8") as f:
        f.write(",".join(map(str, row)) + "\n")


def setup_telemetry_csv(csv_path: Path) -> None:
    """
    Setup telemetry CSV file with proper headers.
    
    Args:
        csv_path: Path to telemetry CSV file
    """
    header = [
        "timestamp", "node_id", "battery_pct", "voltage_v",
        "channel_util_pct", "air_tx_pct", "uptime_s",
        # Environment sensors
        "temperature_c", "humidity_pct", "pressure_hpa", "iaq", "lux",
        # Power monitoring
        "current_ma", 
        "ch1_voltage_v", "ch1_current_ma", "ch2_voltage_v", "ch2_current_ma",
        "ch3_voltage_v", "ch3_current_ma", "ch4_voltage_v", "ch4_current_ma"
    ]
    ensure_header(csv_path, header)


def setup_traceroute_csv(csv_path: Path) -> None:
    """
    Setup traceroute CSV file with proper headers.
    
    Args:
        csv_path: Path to traceroute CSV file
    """
    header = [
        "timestamp", "target_node", "direction", "hop",
        "src", "dst", "db"
    ]
    ensure_header(csv_path, header)