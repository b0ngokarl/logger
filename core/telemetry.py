#!/usr/bin/env python3
"""
Telemetry collection functionality for Meshtastic nodes.

This module provides comprehensive telemetry data collection with:
- Enhanced regex patterns for robust data parsing
- Support for multiple sensor types (environment, power, device)
- Error handling and validation for reliable data collection
- Batch processing capabilities for efficient multi-node monitoring
"""
import re
import sys
from typing import Dict, Optional, Any
from .cli_utils import run_cli, build_meshtastic_command, validate_node_id
from .node_discovery import collect_nodes_detailed


# Core device telemetry patterns - enhanced for alpha reliability
RE_BATT = re.compile(r"Battery level:\s*([0-9.]+)%")
RE_VOLT = re.compile(r"Voltage:\s*([0-9.]+)\s*V")
RE_CHAN = re.compile(r"Total channel utilization:\s*([0-9.]+)%")
RE_AIR = re.compile(r"Transmit air utilization:\s*([0-9.]+)%")
RE_UP = re.compile(r"Uptime:\s*([0-9]+)\s*s")

# Environment sensor patterns - improved for alpha accuracy
RE_TEMP = re.compile(r"Temperature:\s*([0-9.-]+)\s*°?[CF]?")
RE_HUMIDITY = re.compile(r"Humidity:\s*([0-9.]+)%")
RE_PRESSURE = re.compile(r"Pressure:\s*([0-9.]+)\s*(?:hPa|mb|mbar)")
RE_IAQ = re.compile(r"IAQ:\s*([0-9]+)")
RE_LUX = re.compile(r"Lux:\s*([0-9.]+)")

# Power sensor patterns - enhanced for alpha monitoring
RE_CURRENT = re.compile(r"Current:\s*([0-9.]+)\s*(?:mA|A)")
RE_CH_VOLT = re.compile(r"Channel\s*(\d+)\s*voltage:\s*([0-9.]+)\s*V")
RE_CH_CURR = re.compile(r"Channel\s*(\d+)\s*current:\s*([0-9.]+)\s*(?:mA|A)")


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
    telemetry = {}
    
    # Try different telemetry types to get comprehensive data
    telemetry_types = [
        None,  # Default device metrics
        "BME280",  # Temperature, humidity, pressure
        "BME680",  # Temperature, humidity, pressure, gas
        "BMP280",  # Temperature, pressure  
        "SHT31",   # Temperature, humidity
        "INA219",  # Voltage, current
        "INA260",  # Voltage, current, power
        "MAX17048"  # Battery gauge
    ]
    
    for tel_type in telemetry_types:
        cmd_args = ["--request-telemetry"]
        if tel_type:
            cmd_args.append(tel_type)
        cmd_args.extend(["--dest", dest])
        
        cmd = build_meshtastic_command(cmd_args, serial_dev)
        
        success, output = run_cli(cmd, timeout=timeout)
        if success and output:
            # Parse this telemetry type
            parsed_data = _parse_telemetry_output(output)
            telemetry.update(parsed_data)
    
    # If no specific sensors worked, try the basic request
    if not telemetry:
        cmd = build_meshtastic_command(["--request-telemetry", "--dest", dest], serial_dev)
        success, output = run_cli(cmd, timeout=timeout)
        if success:
            telemetry = _parse_telemetry_output(output)
        else:
            print(f"[WARN] Failed to get telemetry for {dest}: {output}", file=sys.stderr)
            return None
    
    return telemetry if telemetry else None


def _parse_telemetry_output(output: str) -> Dict[str, float]:
    """
    Parse telemetry output from meshtastic command and extract all available metrics.
    
    Args:
        output: Raw output from meshtastic command
        
    Returns:
        Dictionary of parsed telemetry data
    """
    telemetry = {}
    
    # Device metrics (basic)
    batt_match = RE_BATT.search(output)
    if batt_match:
        battery_val = float(batt_match.group(1))
        # Clamp battery percentage to reasonable range
        if battery_val > 100:
            battery_val = 100.0
        elif battery_val < 0:
            battery_val = 0.0
        telemetry["battery_pct"] = battery_val
    
    volt_match = RE_VOLT.search(output)
    if volt_match:
        telemetry["voltage_v"] = float(volt_match.group(1))
    
    chan_match = RE_CHAN.search(output)
    if chan_match:
        telemetry["channel_util_pct"] = float(chan_match.group(1))
    
    air_match = RE_AIR.search(output)
    if air_match:
        telemetry["air_tx_pct"] = float(air_match.group(1))
    
    up_match = RE_UP.search(output)
    if up_match:
        telemetry["uptime_s"] = float(up_match.group(1))
    
    # Environment metrics
    temp_match = RE_TEMP.search(output)
    if temp_match:
        telemetry["temperature_c"] = float(temp_match.group(1))
    
    humidity_match = RE_HUMIDITY.search(output)
    if humidity_match:
        telemetry["humidity_pct"] = float(humidity_match.group(1))
    
    pressure_match = RE_PRESSURE.search(output)
    if pressure_match:
        telemetry["pressure_hpa"] = float(pressure_match.group(1))
    
    iaq_match = RE_IAQ.search(output)
    if iaq_match:
        telemetry["iaq"] = float(iaq_match.group(1))
    
    lux_match = RE_LUX.search(output)
    if lux_match:
        telemetry["lux"] = float(lux_match.group(1))
    
    # Power metrics
    current_match = RE_CURRENT.search(output)
    if current_match:
        telemetry["current_ma"] = float(current_match.group(1))
    
    # Multi-channel voltage/current (for power monitoring devices)
    for ch_volt_match in RE_CH_VOLT.finditer(output):
        channel = int(ch_volt_match.group(1))
        voltage = float(ch_volt_match.group(2))
        telemetry[f"ch{channel}_voltage_v"] = voltage
    
    for ch_curr_match in RE_CH_CURR.finditer(output):
        channel = int(ch_curr_match.group(1))
        current = float(ch_curr_match.group(2))
        telemetry[f"ch{channel}_current_ma"] = current
    
    return telemetry


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