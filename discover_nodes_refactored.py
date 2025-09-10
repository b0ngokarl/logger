#!/usr/bin/env python3
"""
Simplified node discovery script using refactored core modules.
"""
import argparse
import sys
from core import discover_all_nodes, collect_nodes_detailed


def main():
    """Main function for node discovery."""
    parser = argparse.ArgumentParser(description="Discover all Meshtastic nodes on the network")
    parser.add_argument("--serial", help="Serial device path, e.g. /dev/ttyACM0 or /dev/ttyUSB0")
    parser.add_argument("--detailed", action="store_true", help="Show detailed node information")
    args = parser.parse_args()
    
    print("[INFO] Discovering all nodes on the network...")
    
    if args.detailed:
        nodes = collect_nodes_detailed(args.serial)
        if nodes:
            print(f"[INFO] Discovered {len(nodes)} nodes with detailed information:")
            for node in nodes:
                print(f"  - {node['id']}: {node.get('user', 'Unknown')} "
                      f"({node.get('hardware', 'Unknown hardware')})")
                if 'battery_pct' in node:
                    print(f"    Battery: {node['battery_pct']}%")
                if 'last_seen' in node:
                    print(f"    Last seen: {node['last_seen']}")
        else:
            print("[WARN] No nodes discovered.")
    else:
        node_ids = discover_all_nodes(args.serial)
        if node_ids:
            print(f"[INFO] Discovered {len(node_ids)} nodes:")
            for node_id in node_ids:
                print(f"  - {node_id}")
        else:
            print("[WARN] No nodes discovered.")
    
    return 0 if (args.detailed and nodes) or (not args.detailed and node_ids) else 1


if __name__ == "__main__":
    sys.exit(main())