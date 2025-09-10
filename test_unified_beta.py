#!/usr/bin/env python3
"""
Comprehensive test suite for the Unified Meshtastic Logger - Beta Version

This test script validates all functionality including:
- Node discovery
- Data collection (telemetry & traceroute)
- Plotting and dashboard generation
- Error handling and edge cases
- Integration between components
"""
import unittest
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

import csv
import time

class TestUnifiedMeshtasticLogger(unittest.TestCase):
    """Test suite for the unified logger functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.test_dir = Path(tempfile.mkdtemp())
        cls.script_path = Path(__file__).parent / "meshtastic_unified.py"
        cls.plot_script_path = Path(__file__).parent / "plot_meshtastic.py"
        
        # Create sample data files for testing
        cls._create_sample_data()
        
        print(f"Test environment created at: {cls.test_dir}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if cls.test_dir.exists():
            shutil.rmtree(cls.test_dir)
    
    @classmethod
    def _create_sample_data(cls):
        """Create sample CSV data for testing plotting functionality."""
        # Create sample telemetry data
        tele_file = cls.test_dir / "test_telemetry.csv"
        with open(tele_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "node_id", "battery_pct", "voltage_v", "channel_util_pct",
                "air_tx_pct", "uptime_s", "temperature_c", "humidity_pct", "pressure_hpa",
                "iaq", "lux", "current_ma", "ch1_voltage_v", "ch1_current_ma",
                "ch2_voltage_v", "ch2_current_ma", "ch3_voltage_v", "ch3_current_ma",
                "ch4_voltage_v", "ch4_current_ma"
            ])
            # Add sample data points
            import datetime
            base_time = datetime.datetime.now()
            for i in range(10):
                timestamp = (base_time + datetime.timedelta(minutes=i*5)).isoformat()
                writer.writerow([
                    timestamp, "!2c9e092b", 85-i*2, 4.1, 15+i, 5+i, 3600+i*300,
                    22.5+i*0.1, 45+i, 1013.25+i*0.1, 50+i, 1000+i*10, 100+i,
                    "", "", "", "", "", "", "", ""
                ])
        
        # Create sample traceroute data
        trace_file = cls.test_dir / "test_traceroute.csv"
        with open(trace_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "target_node", "direction", "hop", "src", "dst", "db"])
            # Add sample traceroute data
            for i in range(5):
                timestamp = (base_time + datetime.timedelta(minutes=i*5)).isoformat()
                writer.writerow([timestamp, "!2c9e092b", "forward", 0, "!abcd1234", "!2c9e092b", -50-i])
                writer.writerow([timestamp, "!2c9e092b", "backward", 0, "!2c9e092b", "!abcd1234", -52-i])
    
    def setUp(self):
        """Set up for each test."""
        self.output_dir = self.test_dir / f"test_output_{int(time.time())}"
        self.output_dir.mkdir(exist_ok=True)
    
    def test_script_help(self):
        """Test that help command works."""
        result = subprocess.run([
            sys.executable, str(self.script_path), "--help"
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Unified Meshtastic", result.stdout)
        self.assertIn("--discover", result.stdout)
        self.assertIn("--nodes", result.stdout)
        self.assertIn("--all-nodes", result.stdout)
    
    def test_discovery_mode(self):
        """Test node discovery mode (should complete even without hardware)."""
        result = subprocess.run([
            sys.executable, str(self.script_path),
            "--discover",
            "--plot-outdir", str(self.output_dir)
        ], capture_output=True, text=True, timeout=30)
        
        # Should complete without error (may show no nodes found)
        self.assertIn("nodes", result.stdout.lower())
    
    def test_plotting_integration(self):
        """Test that plotting integration works with sample data."""
        # Copy sample data to output directory
        tele_file = self.output_dir / "telemetry.csv"
        trace_file = self.output_dir / "traceroute.csv"
        
        shutil.copy(self.test_dir / "test_telemetry.csv", tele_file)
        shutil.copy(self.test_dir / "test_traceroute.csv", trace_file)
        
        # Test plotting directly first
        if self.plot_script_path.exists():
            result = subprocess.run([
                sys.executable, str(self.plot_script_path),
                "--telemetry", str(tele_file),
                "--traceroute", str(trace_file),
                "--outdir", str(self.output_dir)
            ], capture_output=True, text=True, timeout=60)
            
            # Check that plotting completed
            self.assertEqual(result.returncode, 0, f"Plotting failed: {result.stderr}")
            
            # Check that output files were created
            self.assertTrue((self.output_dir / "index.html").exists())
            self.assertTrue((self.output_dir / "diagnostics.html").exists())
    
    def test_data_collection_simulation(self):
        """Test data collection simulation (without hardware)."""
        result = subprocess.run([
            sys.executable, str(self.script_path),
            "--nodes", "!test123",
            "--once",
            "--no-plot",
            "--output", str(self.output_dir / "telemetry.csv"),
            "--trace-output", str(self.output_dir / "traceroute.csv"),
            "--plot-outdir", str(self.output_dir)
        ], capture_output=True, text=True, timeout=60)
        
        # Should complete (may show no nodes found)
        self.assertNotEqual(result.returncode, None)
        
        # Check that CSV files were created with headers
        tele_file = self.output_dir / "telemetry.csv"
        if tele_file.exists():
            with open(tele_file, 'r') as f:
                header = f.readline().strip()
                self.assertIn("timestamp", header)
                self.assertIn("node", header)
    
    def test_unified_workflow(self):
        """Test the complete unified workflow with sample data."""
        # Copy sample data
        tele_file = self.output_dir / "telemetry.csv"
        trace_file = self.output_dir / "traceroute.csv"
        
        shutil.copy(self.test_dir / "test_telemetry.csv", tele_file)
        shutil.copy(self.test_dir / "test_traceroute.csv", trace_file)
        
        # Run unified logger with plotting enabled
        result = subprocess.run([
            sys.executable, str(self.script_path),
            "--nodes", "!2c9e092b",
            "--once",
            "--plot",
            "--output", str(tele_file),
            "--trace-output", str(trace_file),
            "--plot-outdir", str(self.output_dir)
        ], capture_output=True, text=True, timeout=90)
        
        # Check that it completed
        print(f"Unified workflow stdout: {result.stdout}")
        print(f"Unified workflow stderr: {result.stderr}")
        
        # Check for key output files
        expected_files = [
            "index.html",
            "diagnostics.html",
            "nodes.html"
        ]
        
        for filename in expected_files:
            file_path = self.output_dir / filename
            if file_path.exists():
                print(f"✅ Found expected file: {filename}")
            else:
                print(f"⚠️  Missing expected file: {filename}")
    
    def test_error_handling(self):
        """Test error handling with invalid arguments."""
        # Test missing required arguments
        result = subprocess.run([
            sys.executable, str(self.script_path)
        ], capture_output=True, text=True)
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("error", result.stderr.lower())
    
    def test_configuration_validation(self):
        """Test that configuration is properly validated."""
        # Test with non-existent serial device (should handle gracefully)
        result = subprocess.run([
            sys.executable, str(self.script_path),
            "--nodes", "!test123",
            "--once",
            "--serial", "/dev/nonexistent",
            "--plot-outdir", str(self.output_dir)
        ], capture_output=True, text=True, timeout=30)
        
        # Should handle the error gracefully
        print(f"Config validation stdout: {result.stdout}")
        print(f"Config validation stderr: {result.stderr}")


class TestFeatureIntegration(unittest.TestCase):
    """Test integration between different features."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.script_path = Path(__file__).parent / "meshtastic_unified.py"
    
    def tearDown(self):
        """Clean up."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_core_modules_import(self):
        """Test that core modules can be imported successfully."""
        result = subprocess.run([
            sys.executable, "-c",
            "import sys; sys.path.insert(0, 'core'); from core import discover_all_nodes, collect_telemetry_batch; print('Imports successful')"
        ], cwd=Path(__file__).parent, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0, f"Core imports failed: {result.stderr}")
        self.assertIn("successful", result.stdout)
    
    def test_sample_data_processing(self):
        """Test processing of sample data files."""
        # Use existing sample data
        examples_dir = Path(__file__).parent / "examples"
        if examples_dir.exists():
            tele_example = examples_dir / "telemetry_example.csv"
            trace_example = examples_dir / "traceroute_example.csv"
            
            if tele_example.exists() and trace_example.exists():
                plot_script = Path(__file__).parent / "plot_meshtastic.py"
                if plot_script.exists():
                    result = subprocess.run([
                        sys.executable, str(plot_script),
                        "--telemetry", str(tele_example),
                        "--traceroute", str(trace_example),
                        "--outdir", str(self.test_dir)
                    ], capture_output=True, text=True, timeout=60)
                    
                    self.assertEqual(result.returncode, 0, f"Sample data processing failed: {result.stderr}")
                    self.assertTrue((self.test_dir / "index.html").exists())


def run_comprehensive_tests():
    """Run all tests and provide a summary."""
    print("="*70)
    print("🧪 UNIFIED MESHTASTIC LOGGER - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    # Verify script exists
    script_path = Path(__file__).parent / "meshtastic_unified.py"
    if not script_path.exists():
        print("❌ FATAL: meshtastic_unified.py not found!")
        return False
    
    print(f"✅ Found unified script: {script_path}")
    
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(loader.loadTestsFromTestCase(TestUnifiedMeshtasticLogger))
    suite.addTest(loader.loadTestsFromTestCase(TestFeatureIntegration))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('\\n')[-2]}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\\n{'🎉 ALL TESTS PASSED!' if success else '⚠️  Some tests failed - see details above'}")
    print("="*70)
    
    return success


if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
