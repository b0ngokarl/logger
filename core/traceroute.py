#!/usr/bin/env python3
"""
Traceroute functionality for Meshtastic networks.
"""
import re
import sys
from typing import Dict, List, Tuple, Optional
from .cli_utils import run_cli, build_meshtastic_command, validate_node_id


# Regex patterns for parsing traceroute output
RE_HOP = re.compile(r"^\s*\d+\s+(\S+)\s+(\S+)\s+([\d.]+)\s+ms")
RE_FWD_HDR = re.compile(r"^traceroute to ")
RE_BWD_HDR = re.compile(r"^traceroute from ")


def collect_traceroute_cli(dest: str, serial_dev: Optional[str] = None, timeout: int = 30, retries: int = 3) -> Optional[Dict[str, List[Tuple[str, str, float]]]]:
    """
    Collect traceroute data from a Meshtastic node using the CLI.
    
    Args:
        dest: Destination node ID for traceroute
        serial_dev: Optional serial device path
        timeout: Command timeout in seconds
        retries: Number of retry attempts
        
    Returns:
        Dictionary with 'forward' and 'back' traceroute data, or None if failed
    """
    if not validate_node_id(dest):
        print(f"[ERROR] Invalid node ID: {dest}", file=sys.stderr)
        return None
    
    for attempt in range(retries):
        cmd = build_meshtastic_command(["--traceroute", dest], serial_dev)
        
        success, output = run_cli(cmd, timeout=timeout)
        if not success:
            print(f"[WARN] Traceroute attempt {attempt + 1}/{retries} failed for {dest}: {output}", file=sys.stderr)
            if attempt < retries - 1:
                continue
            else:
                return None
        
        # Parse traceroute output
        traceroute_data = _parse_traceroute_output(output)
        if traceroute_data and (traceroute_data.get("forward") or traceroute_data.get("back")):
            return traceroute_data
        
        print(f"[WARN] Traceroute attempt {attempt + 1}/{retries} returned no valid data for {dest}")
    
    return None


def _parse_traceroute_output(output: str) -> Dict[str, List[Tuple[str, str, float]]]:
    """
    Parse traceroute command output.
    
    Args:
        output: Raw traceroute command output
        
    Returns:
        Dictionary with parsed forward and backward traceroute data
    """
    lines = output.splitlines()
    
    forward_hops = []
    backward_hops = []
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        # Check for section headers
        if RE_FWD_HDR.match(line):
            current_section = "forward"
            continue
        elif RE_BWD_HDR.match(line):
            current_section = "back"
            continue
        
        # Parse hop lines
        hop_match = RE_HOP.match(line)
        if hop_match and current_section:
            from_node = hop_match.group(1)
            to_node = hop_match.group(2)
            latency = float(hop_match.group(3))
            
            if current_section == "forward":
                forward_hops.append((from_node, to_node, latency))
            elif current_section == "back":
                backward_hops.append((from_node, to_node, latency))
    
    return {
        "forward": forward_hops,
        "back": backward_hops
    }


def collect_traceroute_batch(node_ids: List[str], serial_dev: Optional[str] = None, timeout: int = 30) -> Dict[str, Dict[str, List[Tuple[str, str, float]]]]:
    """
    Collect traceroute data from multiple nodes.
    
    Args:
        node_ids: List of destination node IDs
        serial_dev: Optional serial device path
        timeout: Command timeout in seconds
        
    Returns:
        Dictionary mapping node IDs to their traceroute data
    """
    results = {}
    
    for node_id in node_ids:
        print(f"[INFO] Running traceroute to {node_id}")
        traceroute_data = collect_traceroute_cli(node_id, serial_dev, timeout)
        if traceroute_data:
            results[node_id] = traceroute_data
            print(f"[INFO] Traceroute completed for {node_id}")
        else:
            print(f"[WARN] Traceroute failed for {node_id}")
    
    return results


def extract_unique_links(traceroute_data: Dict[str, Dict[str, List[Tuple[str, str, float]]]]) -> List[Tuple[str, str]]:
    """
    Extract unique network links from traceroute data.
    
    Args:
        traceroute_data: Dictionary of traceroute data for multiple destinations
        
    Returns:
        List of unique (from_node, to_node) tuples
    """
    links = set()
    
    for dest, routes in traceroute_data.items():
        for direction, hops in routes.items():
            for from_node, to_node, _ in hops:
                links.add((from_node, to_node))
    
    return list(links)


def get_network_topology(traceroute_data: Dict[str, Dict[str, List[Tuple[str, str, float]]]]) -> Dict[str, List[str]]:
    """
    Build network topology from traceroute data.
    
    Args:
        traceroute_data: Dictionary of traceroute data for multiple destinations
        
    Returns:
        Dictionary mapping each node to its neighbors
    """
    topology = {}
    
    for dest, routes in traceroute_data.items():
        for direction, hops in routes.items():
            for from_node, to_node, _ in hops:
                # Add forward connection
                if from_node not in topology:
                    topology[from_node] = []
                if to_node not in topology[from_node]:
                    topology[from_node].append(to_node)
                
                # Add reverse connection (mesh networks are bidirectional)
                if to_node not in topology:
                    topology[to_node] = []
                if from_node not in topology[to_node]:
                    topology[to_node].append(from_node)
    
    return topology