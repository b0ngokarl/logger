#!/usr/bin/env python3
"""
Node page updater class that interfaces with update_node_pages.py

Enhanced with fixes for:
1. Duplicate Node ID display - removes redundant Node ID from info table
2. Improved metric visualization with color coding for signal strength, channel util
3. Battery visualization with visual progress bar and color coding
4. Support for regenerating charts for specific problematic nodes

This module can be used both as a library and as a command-line tool.
"""
import sys
import subprocess
from pathlib import Path
import importlib.util
from typing import Dict, Optional, Any, List

# Known nodes with display issues from previous debugging
KNOWN_PROBLEM_NODES = [
    "2df67288", "277db5ca", "2c9e092b", "75e98c18", "849c4818", "ba656304"
]

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
            # Ensure ID is properly formatted with ! prefix for consistency
            if not node_id.startswith('!'):
                node_id = f"!{node_id}"
                
            # Ensure there's no duplicate node ID in the telemetry data
            if telemetry_data and "id" in telemetry_data:
                # The update_node_pages function will handle the node ID separately
                # so we don't need it in the telemetry data to avoid duplication
                telemetry_data.pop("id", None)
            
            return self.update_node_pages_module.update_node_pages(
                node_id,
                telemetry_data,
                traceroute_data,
                self.output_dir
            )
        except Exception as e:
            print(f"[ERROR] Failed to update node page for {node_id}: {e}", file=sys.stderr)
            return None
            
    def update_multiple_nodes(self, node_ids: List[str]) -> List[str]:
        """Update multiple node pages at once.
        
        Args:
            node_ids: List of node IDs to update
            
        Returns:
            List of successfully updated node IDs
        """
        updated = []
        for node_id in node_ids:
            # Strip any ! prefix for consistency
            normalized_id = node_id.lstrip('!')
            # Add it back for the update function
            node_with_prefix = f"!{normalized_id}"
            
            # Create minimal telemetry data with just the node ID
            # The update_node_pages function will display what it can
            result = self.update_node_page(node_with_prefix, {})
            
            if result:
                updated.append(normalized_id)
                print(f"[INFO] Updated node page for {node_with_prefix}")
            else:
                print(f"[WARN] Failed to update node page for {node_with_prefix}")
                
        return updated
        
    @staticmethod
    def regenerate_node_charts(node_ids: List[str], all_nodes: bool = False) -> bool:
        """Regenerate charts for specific nodes using plot_meshtastic.py.
        
        Args:
            node_ids: List of node IDs to regenerate charts for
            all_nodes: Whether to regenerate charts for all nodes
            
        Returns:
            Boolean indicating success
        """
        # Build the command
        cmd = [
            "python3", "plot_meshtastic.py",
            "--telemetry", "telemetry.csv",
            "--traceroute", "traceroute.csv",
            "--outdir", "plots"
        ]
        
        # Add appropriate flag based on whether we're updating all nodes or specific ones
        if all_nodes:
            cmd.append("--regenerate-charts")
            print("[INFO] Regenerating charts for all nodes")
        else:
            # Strip any ! prefix for consistency
            normalized_ids = [node_id.lstrip('!') for node_id in node_ids]
            cmd.extend(["--regenerate-specific-nodes"] + normalized_ids)
            print(f"[INFO] Regenerating charts for nodes: {', '.join(normalized_ids)}")
        
        # Execute the command
        try:
            result = subprocess.run(cmd, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to regenerate charts: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected error regenerating charts: {e}", file=sys.stderr)
            return False
            
    def fix_duplicate_node_id(self, node_ids: List[str] = None) -> int:
        """Fix duplicate Node ID display in node pages.
        
        Args:
            node_ids: List of node IDs to fix, or None to fix all nodes
            
        Returns:
            Number of fixed pages
        """
        import re
        fixed_count = 0
        
        # Determine which nodes to process
        if node_ids:
            # Process only specific nodes
            node_dirs = [Path(self.output_dir) / f"node_{node_id.lstrip('!')}" for node_id in node_ids]
        else:
            # Process all nodes
            node_dirs = list(Path(self.output_dir).glob("node_*"))
            
        for node_dir in node_dirs:
            if not node_dir.is_dir():
                continue
                
            index_path = node_dir / "index.html"
            if not index_path.exists():
                continue
                
            try:
                # Read the file
                html_content = index_path.read_text(encoding='utf-8')
                
                # Check if this file has already been fixed
                if '<!-- Node page fixed -->' in html_content:
                    continue
                    
                # Remove Node ID from the information table
                # This pattern matches the Node ID row in the information table
                pattern = r'<tr>\s*<td><strong>Node ID</strong></td>\s*<td>[^<]*</td>\s*</tr>'
                html_content = re.sub(pattern, '', html_content)
                
                # Add a marker that this file has been fixed
                html_content = html_content.replace('</head>', '<!-- Node page fixed -->\n</head>')
                
                # Write the updated content back to the file
                index_path.write_text(html_content, encoding='utf-8')
                fixed_count += 1
                print(f"[INFO] Fixed duplicate Node ID in {node_dir.name}")
            except Exception as e:
                print(f"[ERROR] Failed to fix node page {index_path}: {e}", file=sys.stderr)
        
        return fixed_count
    
    def enhance_metrics_visualization(self, node_ids: List[str] = None) -> int:
        """Enhance metrics visualization in node pages.
        
        Args:
            node_ids: List of node IDs to enhance, or None to enhance all nodes
            
        Returns:
            Number of enhanced pages
        """
        import re
        # Check if the enhance_node_visualizations.py script exists
        enhance_script = Path(__file__).parent / "enhance_node_visualizations.py"
        if not enhance_script.exists():
            print(f"[ERROR] enhance_node_visualizations.py not found at {enhance_script}", file=sys.stderr)
            return 0
            
        try:
            # If specific node IDs are provided, create a temporary directory with symlinks
            if node_ids:
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    # Create symlinks to the specific node directories
                    for node_id in node_ids:
                        normalized_id = node_id.lstrip('!')
                        src = Path(self.output_dir) / f"node_{normalized_id}"
                        dst = temp_path / f"node_{normalized_id}"
                        if src.exists():
                            dst.symlink_to(src, target_is_directory=True)
                    
                    # Run the enhancement script on the temp directory
                    result = subprocess.run(
                        ["python3", str(enhance_script), temp_dir],
                        check=True,
                        capture_output=True,
                        text=True
                    )
            else:
                # Run the enhancement script on all nodes
                result = subprocess.run(
                    ["python3", str(enhance_script), self.output_dir],
                    check=True,
                    capture_output=True,
                    text=True
                )
            
            # Extract the number of enhanced pages from the output
            output = result.stdout
            match = re.search(r'Enhanced visualizations in (\d+) node pages', output)
            if match:
                enhanced_count = int(match.group(1))
                return enhanced_count
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to enhance metrics: {e}", file=sys.stderr)
            if 'result' in locals() and result.stderr:
                print(f"[ERROR] Details: {result.stderr}", file=sys.stderr)
            return 0

def main():
    """Command-line interface for the NodePageUpdater."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update node pages and regenerate charts")
    parser.add_argument("--nodes", nargs="+", help="List of node IDs to update")
    parser.add_argument("--all-nodes", action="store_true", help="Update all nodes")
    parser.add_argument("--output-dir", default="plots", help="Output directory")
    parser.add_argument("--regenerate-charts", action="store_true", help="Regenerate charts for nodes")
    parser.add_argument("--fix-known-issues", action="store_true", help="Fix known problematic nodes")
    parser.add_argument("--fix-duplicate-node-id", action="store_true", help="Fix duplicate Node ID display issue")
    parser.add_argument("--enhance-metrics", action="store_true", help="Enhance metrics visualization")
    parser.add_argument("--fix-all", action="store_true", help="Apply all fixes and enhancements")
    
    args = parser.parse_args()
    
    # Create the updater
    updater = NodePageUpdater(output_dir=args.output_dir)
    
    # Handle fixing all issues at once
    if args.fix_all:
        print("[INFO] Applying all fixes and enhancements...")
        # Fix duplicate Node ID for all nodes
        fixed_count = updater.fix_duplicate_node_id()
        print(f"[INFO] Fixed duplicate Node ID in {fixed_count} pages")
        
        # Enhance metrics for all nodes
        enhanced_count = updater.enhance_metrics_visualization()
        print(f"[INFO] Enhanced metrics in {enhanced_count} pages")
        
        # Update known problematic nodes
        updater.update_multiple_nodes(KNOWN_PROBLEM_NODES)
        
        # Regenerate charts for known problematic nodes
        if args.regenerate_charts:
            updater.regenerate_node_charts(KNOWN_PROBLEM_NODES)
            
        return 0
            
    # Handle fixing known issues
    if args.fix_known_issues:
        print("[INFO] Fixing known problematic nodes...")
        updater.update_multiple_nodes(KNOWN_PROBLEM_NODES)
        if args.regenerate_charts:
            updater.regenerate_node_charts(KNOWN_PROBLEM_NODES)
        return 0
        
    # Handle fixing duplicate Node ID
    if args.fix_duplicate_node_id:
        print("[INFO] Fixing duplicate Node ID display...")
        fixed_count = updater.fix_duplicate_node_id()
        print(f"[INFO] Fixed duplicate Node ID in {fixed_count} pages")
        return 0
        
    # Handle enhancing metrics visualization
    if args.enhance_metrics:
        print("[INFO] Enhancing metrics visualization...")
        enhanced_count = updater.enhance_metrics_visualization()
        print(f"[INFO] Enhanced metrics in {enhanced_count} pages")
        return 0
    
    # Default to known problem nodes if no nodes specified
    if not args.nodes and not args.all_nodes:
        print("[WARN] No nodes specified, using known problem nodes")
        nodes = KNOWN_PROBLEM_NODES
    elif args.all_nodes:
        # Get all node directories from the output directory
        try:
            output_path = Path(args.output_dir)
            node_dirs = [d.name.replace("node_", "") for d in output_path.iterdir()
                        if d.is_dir() and d.name.startswith("node_")]
            if not node_dirs:
                print("[WARN] No node directories found in output directory")
                return 1
            nodes = node_dirs
        except Exception as e:
            print(f"[ERROR] Failed to list node directories: {e}", file=sys.stderr)
            return 1
    else:
        nodes = args.nodes
    
    # Update the pages
    updated_nodes = updater.update_multiple_nodes(nodes)
    
    if not updated_nodes:
        print("[WARN] No node pages were updated")
        return 1
        
    # Regenerate charts if requested
    if args.regenerate_charts:
        if not updater.regenerate_node_charts(updated_nodes):
            print("[ERROR] Failed to regenerate some charts")
            return 1
            
    print(f"[SUCCESS] Updated {len(updated_nodes)} node pages")
    return 0

if __name__ == "__main__":
    sys.exit(main())
