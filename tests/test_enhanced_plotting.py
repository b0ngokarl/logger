#!/usr/bin/env python3
"""
Tests for enhanced plotting functionality.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from plot_meshtastic import (
    read_merge_telemetry, read_merge_traceroute, 
    create_timestamped_output_dir, write_comprehensive_nodes_list,
    write_root_index, ensure_outdir
)


class TestEnhancedPlotting(unittest.TestCase):
    """Test enhanced plotting functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.examples_dir = Path(__file__).parent.parent / "examples"
        
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_read_merge_telemetry(self):
        """Test telemetry CSV reading and merging."""
        tele_file = self.examples_dir / "telemetry_example.csv"
        if tele_file.exists():
            df = read_merge_telemetry([str(tele_file)])
            self.assertFalse(df.empty)
            self.assertIn("node", df.columns)
            self.assertIn("battery_pct", df.columns)
            self.assertIn("voltage_v", df.columns)
    
    def test_read_merge_traceroute(self):
        """Test traceroute CSV reading and merging."""
        trace_file = self.examples_dir / "traceroute_example.csv"
        if trace_file.exists():
            df = read_merge_traceroute([str(trace_file)])
            self.assertFalse(df.empty)
            self.assertIn("dest", df.columns)
            self.assertIn("direction", df.columns)
            self.assertIn("hop_index", df.columns)
    
    def test_create_timestamped_output_dir(self):
        """Test timestamped output directory creation."""
        base_dir = self.temp_dir / "test_output"
        
        # Test without history preservation
        result = create_timestamped_output_dir(base_dir, False)
        self.assertEqual(result, base_dir)
        
        # Test with history preservation  
        timestamped_dir, latest_link = create_timestamped_output_dir(base_dir, True)
        self.assertTrue(str(timestamped_dir).startswith(str(base_dir / "run_")))
        self.assertEqual(latest_link, base_dir / "latest")
    
    def test_ensure_outdir(self):
        """Test output directory creation."""
        test_dir = self.temp_dir / "new_output"
        self.assertFalse(test_dir.exists())
        
        ensure_outdir(test_dir)
        self.assertTrue(test_dir.exists())
        self.assertTrue(test_dir.is_dir())
    
    def test_write_root_index(self):
        """Test enhanced root index HTML generation."""
        ensure_outdir(self.temp_dir)
        
        # Create some dummy files to simulate chart generation
        (self.temp_dir / "traceroute_hops.png").touch()
        (self.temp_dir / "topology_test_forward.png").touch()
        
        write_root_index(self.temp_dir)
        
        index_file = self.temp_dir / "index.html"
        self.assertTrue(index_file.exists())
        
        content = index_file.read_text()
        self.assertIn("Meshtastic Network Dashboard", content)
        self.assertIn("Network Monitoring & Analysis Portal", content)
        self.assertIn("traceroute_hops.png", content)
        self.assertIn("topology_test_forward.png", content)
    
    def test_write_comprehensive_nodes_list(self):
        """Test comprehensive nodes list generation."""
        ensure_outdir(self.temp_dir)
        
        # Create dummy dashboard info
        dashboards = {
            "!testnode1": self.temp_dir / "node_testnode1",
            "!testnode2": self.temp_dir / "node_testnode2"
        }
        
        write_comprehensive_nodes_list(self.temp_dir, dashboards)
        
        nodes_file = self.temp_dir / "nodes.html"
        self.assertTrue(nodes_file.exists())
        
        content = nodes_file.read_text()
        self.assertIn("Network Nodes Directory", content)
        self.assertIn("!testnode1", content)
        self.assertIn("!testnode2", content)
        self.assertIn("Total Nodes", content)
    
    def test_html_structure_and_styling(self):
        """Test that generated HTML has proper structure and CSS."""
        ensure_outdir(self.temp_dir)
        write_root_index(self.temp_dir)
        
        content = (self.temp_dir / "index.html").read_text()
        
        # Check for proper HTML5 structure
        self.assertIn("<!doctype html>", content.lower())
        self.assertIn('<html lang="en">', content)
        self.assertIn('<meta charset=', content)
        self.assertIn('viewport', content)
        
        # Check for enhanced CSS features
        self.assertIn("linear-gradient", content)
        self.assertIn("backdrop-filter", content)
        self.assertIn("grid-template-columns", content)
        self.assertIn("border-radius", content)
        
        # Check for responsive design
        self.assertIn("@media", content)
        self.assertIn("max-width", content)
    
    def test_icon_and_emoji_usage(self):
        """Test that appropriate icons and emojis are used for better UX."""
        ensure_outdir(self.temp_dir)
        
        # Create dummy files to trigger navigation generation  
        (self.temp_dir / "dashboards.html").touch()
        (self.temp_dir / "diagnostics.html").touch()
        (self.temp_dir / "nodes.html").touch()
        
        write_root_index(self.temp_dir)
        
        content = (self.temp_dir / "index.html").read_text()
        
        # Check for meaningful emojis/icons
        self.assertIn("🌐", content)  # Network icon
        self.assertIn("📊", content)  # Dashboard icon  
        self.assertIn("🔍", content)  # Diagnostics icon
        self.assertIn("📋", content)  # Nodes list icon


class TestHistoryPreservation(unittest.TestCase):
    """Test history preservation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_timestamped_directories(self):
        """Test that timestamped directories preserve history."""
        base_dir = self.temp_dir / "plots"
        
        # Create first run
        run1_dir, latest_link = create_timestamped_output_dir(base_dir, True)
        ensure_outdir(run1_dir)
        (run1_dir / "test1.txt").write_text("first run")
        
        # Create second run  
        import time
        time.sleep(1)  # Ensure different timestamp
        run2_dir, _ = create_timestamped_output_dir(base_dir, True)
        ensure_outdir(run2_dir)
        (run2_dir / "test2.txt").write_text("second run")
        
        # Verify both runs exist
        self.assertTrue((run1_dir / "test1.txt").exists())
        self.assertTrue((run2_dir / "test2.txt").exists())
        self.assertNotEqual(run1_dir, run2_dir)
        
        # Verify they're in the same base directory
        self.assertEqual(run1_dir.parent, base_dir)
        self.assertEqual(run2_dir.parent, base_dir)


if __name__ == "__main__":
    unittest.main()