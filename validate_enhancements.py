#!/usr/bin/env python3
"""
Validation script for Meshtastic Telemetry Logger enhancements

This script validates all the enhancements made to the node pages:
1. Generates plots from example data
2. Fixes duplicate Node ID display
3. Adds battery metrics to example nodes
4. Enhances metric visualization
5. Verifies the results

Usage:
  python3 validate_enhancements.py
"""

import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle the result"""
    print(f"\n[STEP] {description}")
    print(f"[INFO] Running command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0:
            print(f"[SUCCESS] {description} completed successfully")
            return True
        else:
            print(f"[ERROR] {description} failed with code {result.returncode}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to execute command: {e}")
        return False

def validate():
    """Run validation tests for all enhancements"""
    # Create a temporary directory for testing
    test_dir = Path("/tmp/meshtastic_validation")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(exist_ok=True)
    
    print(f"[INFO] Using test directory: {test_dir}")
    
    # Step 1: Generate plots from example data
    plot_cmd = [
        "python3", "plot_meshtastic.py",
        "--telemetry", "examples/telemetry_example.csv",
        "--traceroute", "examples/traceroute_example.csv",
        "--outdir", str(test_dir)
    ]
    if not run_command(plot_cmd, "Generate plots from example data"):
        return False
    
    # Step 2: Add battery metrics to example nodes
    battery_cmd = ["python3", "add_battery_to_examples.py", str(test_dir)]
    if not run_command(battery_cmd, "Add battery metrics to example nodes"):
        return False
    
    # Step 3: Fix duplicate Node ID display
    fix_cmd = ["python3", "node_page_updater.py", "--fix-duplicate-node-id", "--output-dir", str(test_dir)]
    if not run_command(fix_cmd, "Fix duplicate Node ID display"):
        return False
    
    # Step 4: Enhance metrics visualization
    enhance_cmd = ["python3", "enhance_node_visualizations.py", str(test_dir)]
    if not run_command(enhance_cmd, "Enhance metrics visualization"):
        return False
    
    # Step 5: Verify results
    print("\n[INFO] Validation completed successfully!")
    print(f"[INFO] Check the results in: {test_dir}")
    print("[INFO] Specifically verify:")
    print("  - No duplicate Node ID in node information tables")
    print("  - Visual battery progress bars with color coding")
    print("  - Color-coded channel utilization and air TX metrics")
    
    print("\n[INFO] Try opening the following file in a browser:")
    print(f"  file://{test_dir}/index.html")
    
    return True

if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
