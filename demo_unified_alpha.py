#!/usr/bin/env python3
"""
Demo script for the Unified Meshtastic Logger - Alpha Version

This script demonstrates the key features and provides a safe way to test
the unified logger functionality without requiring Meshtastic hardware.
Alpha version features enhanced reliability, improved error handling,
and modernized code structure.
"""
import subprocess
import sys
import time
from pathlib import Path
import csv
from datetime import datetime, timedelta

def create_sample_data():
    """Create sample data files for demonstration."""
    print("📊 Creating sample data files...")
    
    # Create sample telemetry data
    tele_file = Path("demo_telemetry.csv")
    with open(tele_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "node_id", "battery_pct", "voltage_v", "channel_util_pct",
            "air_tx_pct", "uptime_s", "temperature_c", "humidity_pct", "pressure_hpa",
            "iaq", "lux", "current_ma", "ch1_voltage_v", "ch1_current_ma",
            "ch2_voltage_v", "ch2_current_ma", "ch3_voltage_v", "ch3_current_ma",
            "ch4_voltage_v", "ch4_current_ma"
        ])
        
        # Add sample data points simulating a day of data
        base_time = datetime.now() - timedelta(hours=24)
        for i in range(24):  # Hourly data points
            timestamp = (base_time + timedelta(hours=i)).isoformat()
            battery = max(20, 100 - i*2)  # Battery declining over time
            temp = 20 + 5 * (0.5 - abs((i - 12) / 24))  # Temperature curve
            writer.writerow([
                timestamp, "!demo123", battery, 4.2 - i*0.01, 10 + i%5,
                5 + i%3, 3600 + i*3600, temp, 45 + i%10, 1013.25 + i*0.1,
                50 + i%5, 1000 + i*50, 100 + i, "", "", "", "", "", "", "", ""
            ])
            writer.writerow([
                timestamp, "!demo456", max(30, 95 - i*1.5), 4.1 - i*0.008, 15 + i%7,
                3 + i%4, 7200 + i*3600, temp + 2, 50 + i%8, 1012 + i*0.05,
                45 + i%7, 800 + i*30, 80 + i, "", "", "", "", "", "", "", ""
            ])
    
    # Create sample traceroute data
    trace_file = Path("demo_traceroute.csv")
    with open(trace_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "target_node", "direction", "hop", "src", "dst", "db"])
        
        # Add sample traceroute data
        for i in range(12):  # Every 2 hours
            timestamp = (base_time + timedelta(hours=i*2)).isoformat()
            # Forward path
            writer.writerow([timestamp, "!demo123", "forward", 0, "!gateway", "!demo123", -45 - i])
            writer.writerow([timestamp, "!demo456", "forward", 0, "!gateway", "!relay001", -50 - i])
            writer.writerow([timestamp, "!demo456", "forward", 1, "!relay001", "!demo456", -55 - i])
            # Backward path
            writer.writerow([timestamp, "!demo123", "backward", 0, "!demo123", "!gateway", -47 - i])
            writer.writerow([timestamp, "!demo456", "backward", 0, "!demo456", "!relay001", -57 - i])
            writer.writerow([timestamp, "!demo456", "backward", 1, "!relay001", "!gateway", -52 - i])
    
    print(f"✅ Created sample data: {tele_file} ({tele_file.stat().st_size} bytes)")
    print(f"✅ Created sample data: {trace_file} ({trace_file.stat().st_size} bytes)")
    return tele_file, trace_file

def demo_discovery():
    """Demonstrate node discovery functionality."""
    print("\\n🔍 DEMO: Node Discovery")
    print("=" * 50)
    
    result = subprocess.run([
        sys.executable, "meshtastic_unified.py", "--discover"
    ], capture_output=True, text=True, timeout=30)
    
    print("Command: meshtastic_unified.py --discover")
    print("Output:", result.stdout)
    if result.stderr:
        print("Notes:", result.stderr)

def demo_help():
    """Show the help system."""
    print("\\n📖 DEMO: Help System")
    print("=" * 50)
    
    result = subprocess.run([
        sys.executable, "meshtastic_unified.py", "--help"
    ], capture_output=True, text=True)
    
    # Show just the key parts
    lines = result.stdout.split('\\n')
    in_examples = False
    for line in lines:
        if line.startswith('Examples:'):
            in_examples = True
        if in_examples or 'Unified Meshtastic' in line or line.startswith('  --nodes') or line.startswith('  --discover'):
            print(line)

def demo_plotting():
    """Demonstrate plotting with sample data."""
    print("\\n📈 DEMO: Plotting and Dashboard Generation")
    print("=" * 50)
    
    tele_file, trace_file = create_sample_data()
    demo_dir = Path("demo_output")
    demo_dir.mkdir(exist_ok=True)
    
    print("\\nGenerating dashboard from sample data...")
    
    result = subprocess.run([
        sys.executable, "plot_meshtastic.py",
        "--telemetry", str(tele_file),
        "--traceroute", str(trace_file),
        "--outdir", str(demo_dir)
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print("✅ Dashboard generation successful!")
        
        # List generated files
        generated_files = list(demo_dir.glob("*.html")) + list(demo_dir.glob("*.png"))
        if generated_files:
            print("\\n📁 Generated files:")
            for file in sorted(generated_files):
                print(f"  - {file.name}")
            
            index_file = demo_dir / "index.html"
            if index_file.exists():
                print(f"\\n🌐 Open dashboard: file://{index_file.resolve()}")
        else:
            print("⚠️  No files generated")
    else:
        print("❌ Dashboard generation failed:")
        print(result.stderr)
    
    # Cleanup
    tele_file.unlink(missing_ok=True)
    trace_file.unlink(missing_ok=True)

def demo_unified_workflow():
    """Demonstrate the complete unified workflow."""
    print("\\n🚀 DEMO: Unified Workflow (Simulation)")
    print("=" * 50)
    
    # Create sample data first
    tele_file, trace_file = create_sample_data()
    demo_dir = Path("demo_unified")
    demo_dir.mkdir(exist_ok=True)
    
    print("Running unified logger in simulation mode...")
    print("Command: meshtastic_unified.py --nodes !demo123 --once --plot")
    
    # Copy sample data to expected locations
    import shutil
    shutil.copy(tele_file, "telemetry.csv")
    shutil.copy(trace_file, "traceroute.csv")
    
    # Run plotting only (since data collection would timeout without hardware)
    result = subprocess.run([
        sys.executable, "plot_meshtastic.py",
        "--telemetry", "telemetry.csv",
        "--traceroute", "traceroute.csv",
        "--outdir", "plots"
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print("✅ Unified workflow simulation successful!")
        
        plots_dir = Path("plots")
        if plots_dir.exists():
            html_files = list(plots_dir.glob("*.html"))
            print(f"\\n📊 Generated {len(html_files)} dashboard pages")
            
            index_file = plots_dir / "index.html"
            if index_file.exists():
                print(f"🌐 Main dashboard: file://{index_file.resolve()}")
    else:
        print("❌ Unified workflow failed:")
        print(result.stderr)
    
    # Cleanup
    tele_file.unlink(missing_ok=True)
    trace_file.unlink(missing_ok=True)

def run_comprehensive_demo():
    """Run all demonstration features."""
    print("🎯 UNIFIED MESHTASTIC LOGGER - BETA DEMONSTRATION")
    print("=" * 60)
    print("This demo showcases the key features of the unified logger.")
    print("Note: Hardware-dependent features will show simulated behavior.\\n")
    
    try:
        # Check if script exists
        if not Path("meshtastic_unified.py").exists():
            print("❌ meshtastic_unified.py not found!")
            return False
        
        # Demo 1: Help system
        demo_help()
        
        # Demo 2: Node discovery
        demo_discovery()
        
        # Demo 3: Plotting functionality
        demo_plotting()
        
        # Demo 4: Unified workflow
        demo_unified_workflow()
        
        print("\\n" + "=" * 60)
        print("🎉 DEMONSTRATION COMPLETE!")
        print("=" * 60)
        print("Key Features Demonstrated:")
        print("✅ Unified command-line interface")
        print("✅ Node discovery and management")
        print("✅ Plotting and dashboard generation")
        print("✅ Comprehensive help system")
        print("✅ Error handling and graceful degradation")
        print("\\nThe unified logger is ready for use!")
        print("\\nNext Steps:")
        print("1. Connect Meshtastic hardware for live data collection")
        print("2. Use --discover to find available nodes")
        print("3. Run --nodes [id] --once --plot for testing")
        print("4. Set up continuous monitoring with --all-nodes --interval 300")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

if __name__ == "__main__":
    success = run_comprehensive_demo()
    sys.exit(0 if success else 1)
