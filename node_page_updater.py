#!/usr/bin/env python3
"""
Node page updater class that interfaces with update_node_pages.py
"""
import sys
from pathlib import Path
import importlib.util
from typing import Dict, Optional, Any

class NodePageUpdater:
    """Class to update node-specific pages with telemetry and traceroute data."""
    
    def __init__(self, output_dir: str = "plots"):
        """Initialize the updater with the output directory."""
        self.output_dir = output_dir
        self.update_node_pages_module = None
        
        # Try to load the update_node_pages module
        update_node_pages_path = Path(__file__).parent / "update_node_pages.py"
        if update_node_pages_path.exists():
            try:
                spec = importlib.util.spec_from_file_location("update_node_pages", update_node_pages_path)
                if spec and spec.loader:
                    self.update_node_pages_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(self.update_node_pages_module)
            except Exception as e:
                print(f"[ERROR] Failed to load update_node_pages module: {e}", file=sys.stderr)
        else:
            print(f"[ERROR] update_node_pages.py not found at {update_node_pages_path}", file=sys.stderr)
    
    def update_node_page(self, node_id: str, telemetry_data: Dict[str, Any] = None, 
                       traceroute_data: Dict[str, Any] = None) -> Optional[str]:
        """Update a node-specific page with telemetry and traceroute data.
        
        Args:
            node_id: The node ID
            telemetry_data: Dictionary of telemetry metrics
            traceroute_data: Dictionary of traceroute information
            
        Returns:
            Path to the created HTML file or None if failed
        """
        if not self.update_node_pages_module:
            print("[ERROR] Cannot update node page: update_node_pages module not loaded", file=sys.stderr)
            return None
        
        try:
            return self.update_node_pages_module.update_node_pages(
                node_id,
                telemetry_data,
                traceroute_data,
                self.output_dir
            )
        except Exception as e:
            print(f"[ERROR] Failed to update node page for {node_id}: {e}", file=sys.stderr)
            return None
