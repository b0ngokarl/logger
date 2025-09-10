#!/usr/bin/env python3
"""
Telemetry collection functionality for Meshtastic nodes.
"""
import re
import sys
from typing import Dict, Optional, Any
from .cli_utils import run_cli, build_meshtastic_command, validate_node_id
from .node_discovery import collect_nodes_detailed


# Regex patterns for parsing telemetry data
RE_BATT = re.compile(r"Battery level:\s*([0-9.]+)%")
RE_VOLT = re.compile(r"Voltage:\s*([0-9.]+)\s*V")
RE_CHAN = re.compile(r"Total channel utilization:\s*([0-9.]+)%")
RE_AIR = re.compile(r"Transmit air utilization:\s*([0-9.]+)%")
RE_UP = re.compile(r"Uptime:\s*([0-9]+)\s*s")


def collect_telemetry_cli(dest: str, serial_dev: Optional[str] = None, timeout: int = 30) -> Optional[Dict[str, float]]:
    """
    Collect telemetry data from a Meshtastic node using the CLI.
    
    Args:
        dest: Node ID to collect telemetry from (should start with !)
        serial_dev: Optional serial device path
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary of telemetry data or None if failed
    """
    # Validate node ID
    if not validate_node_id(dest):
        print(f"[ERROR] Invalid node ID: {dest}", file=sys.stderr)
        return None
    
    # Try to get telemetry from the --nodes command first (more reliable)
    nodes_data = collect_nodes_detailed(serial_dev, timeout)
    
    # Look for our target node in the nodes data
    target_node = None
    for node in nodes_data:
        if node.get("id") == dest:
            target_node = node
            break
    
    if target_node:
        telemetry = {}
        
        # Extract available telemetry data
        if "battery_pct" in target_node:
            telemetry["battery_pct"] = target_node["battery_pct"]
        
        # Try to get voltage from direct telemetry command if needed
        if not telemetry or "voltage_v" not in telemetry:
            additional_data = _collect_direct_telemetry(dest, serial_dev, timeout)
            if additional_data:
                telemetry.update(additional_data)
        
        return telemetry if telemetry else None
    
    # Fallback to direct telemetry collection
    return _collect_direct_telemetry(dest, serial_dev, timeout)


def _collect_direct_telemetry(dest: str, serial_dev: Optional[str] = None, timeout: int = 30) -> Optional[Dict[str, float]]:
    """
    Collect telemetry directly using meshtastic --request-telemetry --dest command.
    
    Args:
        dest: Node ID to collect telemetry from
        serial_dev: Optional serial device path
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary of telemetry data or None if failed
    """
    cmd = build_meshtastic_command(["--request-telemetry", "--dest", dest], serial_dev)
    
    success, output = run_cli(cmd, timeout=timeout)
    if not success:
        print(f"[WARN] Failed to get telemetry for {dest}: {output}", file=sys.stderr)
        return None
    
    # Parse telemetry output using regex patterns
    telemetry = {}
    
    # Battery level
    batt_match = RE_BATT.search(output)
    if batt_match:
        telemetry["battery_pct"] = float(batt_match.group(1))
    
    # Voltage
    volt_match = RE_VOLT.search(output)
    if volt_match:
        telemetry["voltage_v"] = float(volt_match.group(1))
    
    # Channel utilization
    chan_match = RE_CHAN.search(output)
    if chan_match:
        telemetry["channel_util_pct"] = float(chan_match.group(1))
    
    # Air time utilization
    air_match = RE_AIR.search(output)
    if air_match:
        telemetry["air_tx_pct"] = float(air_match.group(1))
    
    # Uptime
    up_match = RE_UP.search(output)
    if up_match:
        telemetry["uptime_s"] = float(up_match.group(1))
    
    return telemetry if telemetry else None


def collect_telemetry_batch(node_ids: list, serial_dev: Optional[str] = None, timeout: int = 30) -> Dict[str, Dict[str, float]]:
    """
    Collect telemetry data from multiple nodes.
    
    Args:
        node_ids: List of node IDs to collect telemetry from
        serial_dev: Optional serial device path
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary mapping node IDs to their telemetry data
    """
    results = {}
    
    for node_id in node_ids:
        print(f"[INFO] Collecting telemetry for {node_id}")
        telemetry = collect_telemetry_cli(node_id, serial_dev, timeout)
        if telemetry:
            results[node_id] = telemetry
            print(f"[INFO] Telemetry collected for {node_id}")
        else:
            print(f"[WARN] No telemetry data for {node_id}")
    
    return results