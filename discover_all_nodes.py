#!/usr/bin/env python3
"""
Discover all nodes in Meshtastic network.
"""
import subprocess
import argparse
import sys
from typing import List, Optional, Tuple

def run_cli(cmd: List[str], timeout: int=30) -> Tuple[bool, str]:
    """Run a CLI command and return success flag and output."""
    if not isinstance(cmd, list) or not cmd:
        return False, "[INVALID_CMD]"
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=timeout, shell=False)
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output
    except subprocess.TimeoutExpired:
        return False, "[TIMEOUT]"

def discover_all_nodes(serial_dev: Optional[str]=None) -> List[str]:
    """Discover all nodes on the mesh network.
    
    Args:
        serial_dev: Optional serial device path (e.g., /dev/ttyUSB0)
        
    Returns:
        List of node IDs
    """
    cmd = ["meshtastic", "--nodes"]
    if serial_dev:
        cmd.extend(["--port", serial_dev])
    
    success, output = run_cli(cmd, timeout=30)
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
                if node_id and node_id not in ("ID", ""):
                    node_ids.append(node_id)
    
    return node_ids

def parse_args():
    parser = argparse.ArgumentParser(description="Discover all Meshtastic nodes on the network")
    parser.add_argument("--serial", help="Serial device path, e.g. /dev/ttyACM0 or /dev/ttyUSB0")
    return parser.parse_args()

def main():
    args = parse_args()
    
    print("[INFO] Discovering all nodes on the network...")
    nodes = discover_all_nodes(args.serial)
    
    if nodes:
        print(f"[INFO] Discovered {len(nodes)} nodes:")
        for node in nodes:
            print(f"  - {node}")
    else:
        print("[WARN] No nodes discovered.")
    
    return nodes

if __name__ == "__main__":
    main()
