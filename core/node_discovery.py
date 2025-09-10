#!/usr/bin/env python3
"""
Node discovery functionality for Meshtastic networks.
"""
import sys
from typing import List, Dict, Optional, Any
from .cli_utils import run_cli, build_meshtastic_command, validate_node_id


def discover_all_nodes(serial_dev: Optional[str] = None, timeout: int = 30) -> List[str]:
    """
    Discover all nodes on the mesh network.
    
    Args:
        serial_dev: Optional serial device path (e.g., /dev/ttyUSB0)
        timeout: Command timeout in seconds
        
    Returns:
        List of node IDs
    """
    cmd = build_meshtastic_command(["--nodes"], serial_dev)
    
    success, output = run_cli(cmd, timeout=timeout)
    if not success:
        print("[ERROR] Failed to discover nodes", file=sys.stderr)
        return []
    
    # Parse the output to extract node IDs
    node_ids = []
    lines = output.splitlines()
    for line in lines:
        if '│' in line:  # Table row
            parts = line.split('│')
            if len(parts) > 2:  # Should have at least ID column
                node_id = parts[2].strip()
                if node_id and node_id not in ("ID", "") and validate_node_id(node_id):
                    node_ids.append(node_id)
    
    return node_ids


def collect_nodes_detailed(serial_dev: Optional[str] = None, timeout: int = 30) -> List[Dict[str, Any]]:
    """
    Collect detailed information about all nodes on the mesh network.
    
    Args:
        serial_dev: Optional serial device path
        timeout: Command timeout in seconds
        
    Returns:
        List of node dictionaries with detailed information
    """
    cmd = build_meshtastic_command(["--nodes"], serial_dev)
    
    success, output = run_cli(cmd, timeout=timeout)
    if not success:
        print("[ERROR] Failed to collect detailed node info", file=sys.stderr)
        return []
    
    nodes = []
    lines = output.splitlines()
    
    for line in lines:
        if '│' in line and line.count('│') >= 16:  # Full table row
            parts = line.split('│')
            if len(parts) > 16:
                try:
                    node_data = {}
                    
                    # Extract basic node information
                    node_data["user"] = parts[1].strip() if len(parts) > 1 else "Unknown"
                    node_data["id"] = parts[2].strip() if len(parts) > 2 else ""
                    node_data["aka"] = parts[3].strip() if len(parts) > 3 else ""
                    node_data["hardware"] = parts[4].strip() if len(parts) > 4 else ""
                    node_data["key"] = parts[5].strip() if len(parts) > 5 else ""
                    node_data["firmware"] = parts[6].strip() if len(parts) > 6 else ""
                    
                    # Location data
                    node_data["latitude"] = parts[7].strip() if len(parts) > 7 else ""
                    node_data["longitude"] = parts[8].strip() if len(parts) > 8 else ""
                    node_data["altitude"] = parts[9].strip() if len(parts) > 9 else ""
                    
                    # Battery information
                    battery_str = parts[10].strip() if len(parts) > 10 else ""
                    if battery_str and battery_str != 'N/A':
                        if '%' in battery_str:
                            node_data["battery_pct"] = float(battery_str.replace('%', ''))
                        elif battery_str == "Powered":
                            node_data["battery_pct"] = 100.0
                    
                    # Signal strength
                    signal_str = parts[13].strip() if len(parts) > 13 else ""
                    if signal_str and signal_str != 'N/A':
                        node_data["signal_strength"] = signal_str
                    
                    # Hop count
                    hop_str = parts[14].strip() if len(parts) > 14 else ""
                    if hop_str and hop_str != 'N/A':
                        node_data["hops"] = hop_str
                    
                    # Last heard timestamp
                    node_data["last_seen"] = parts[16].strip() if len(parts) > 16 else ""
                    
                    # Only add node if it has a valid ID
                    if node_data["id"] and validate_node_id(node_data["id"]):
                        nodes.append(node_data)
                        
                except (ValueError, IndexError) as e:
                    print(f"[WARN] Failed to parse node line: {line[:50]}..., error: {e}", file=sys.stderr)
                    continue
    
    return nodes


def normalize_node_id(node_id: str) -> str:
    """
    Normalize a node ID by ensuring it has the proper format.
    
    Args:
        node_id: Raw node ID
        
    Returns:
        Normalized node ID with ! prefix
    """
    if not node_id:
        return node_id
        
    # Remove any existing ! prefix and add it back
    normalized = node_id.strip('!')
    return f"!{normalized}" if normalized else node_id