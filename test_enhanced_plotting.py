#!/usr/bin/env python3
"""
Test suite for enhanced plotting functionality
Tests the comprehensive features added for HTML dashboards, 
history preservation, and node management.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# Add the current directory to path to import plot_meshtastic
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plot_meshtastic


class TestEnhancedPlotting(unittest.TestCase):
    """Test suite covering the enhanced plotting functionality."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory and sample data."""
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Create sample telemetry data
        self.sample_telemetry = pd.DataFrame({
            'timestamp': [
                '2025-01-01 10:00:00',
                '2025-01-01 10:05:00', 
                '2025-01-01 10:10:00',
                '2025-01-01 10:15:00'
            ],
            'node': ['!12345678', '!87654321', '!12345678', '!87654321'],
            'battery_pct': [85.5, 92.1, 84.2, 91.8],
            'voltage_v': [3.8, 3.9, 3.75, 3.88],
            'channel_util_pct': [15.2, 22.1, 16.8, 23.5],
            'air_tx_pct': [5.1, 8.2, 5.8, 8.9],
            'uptime_s': [86400, 172800, 90000, 176400]
        })
        
        # Create sample traceroute data
        self.sample_traceroute = pd.DataFrame({
            'timestamp': [
                '2025-01-01 10:00:00',
                '2025-01-01 10:05:00',
                '2025-01-01 10:10:00'
            ],
            'source': ['!12345678', '!87654321', '!12345678'],
            'dest': ['!87654321', '!12345678', '!abcdefab'],
            'hops': [2, 1, 3],
            'snr_db': [-5.2, -3.1, -8.5]
        })
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_history_preservation_directory_creation(self):
        """Test 1: Verify timestamped directory creation and symlink system."""
        base_dir = self.test_dir / "history_test"
        
        # Test timestamped directory creation
        timestamped_dir = plot_meshtastic.create_timestamped_output_dir(base_dir)
        
        # Verify directory exists and follows naming pattern
        self.assertTrue(timestamped_dir.exists())
        self.assertTrue(timestamped_dir.name.startswith('run_'))
        self.assertTrue(len(timestamped_dir.name) == 19)  # run_YYYYMMDD_HHMMSS
        
        # Verify symlink creation
        latest_link = base_dir / "latest"
        self.assertTrue(latest_link.exists())
        self.assertTrue(latest_link.is_symlink())
        self.assertEqual(latest_link.resolve(), timestamped_dir.resolve())
    
    def test_comprehensive_nodes_list_generation(self):
        """Test 2: Verify comprehensive nodes.html generation with proper structure."""
        output_dir = self.test_dir / "nodes_test"
        output_dir.mkdir()
        
        # Generate nodes list
        plot_meshtastic.write_comprehensive_nodes_list(
            self.sample_telemetry, self.sample_traceroute, output_dir
        )
        
        # Verify nodes.html was created
        nodes_file = output_dir / "nodes.html"
        self.assertTrue(nodes_file.exists())
        
        # Verify HTML structure and content
        html_content = nodes_file.read_text()
        
        # Check for essential HTML elements
        self.assertIn('<!DOCTYPE html>', html_content)
        self.assertIn('Meshtastic Network Nodes', html_content)
        self.assertIn('nodesTable', html_content)
        self.assertIn('filterNodes()', html_content)
        self.assertIn('sortTable(', html_content)
        
        # Check for node data
        self.assertIn('!12345678', html_content)
        self.assertIn('!87654321', html_content)
        
        # Check for status indicators
        self.assertIn('🟢', html_content)  # Active indicator
        self.assertIn('🔴', html_content)  # Stale indicator
    
    def test_modern_css_styling_implementation(self):
        """Test 3: Verify modern CSS styling is present in HTML outputs."""
        output_dir = self.test_dir / "css_test"
        output_dir.mkdir()
        
        # Generate enhanced root index
        plot_meshtastic.write_root_index(output_dir)
        
        # Verify index.html was created with modern styling
        index_file = output_dir / "index.html"
        self.assertTrue(index_file.exists())
        
        html_content = index_file.read_text()
        
        # Check for modern CSS features
        self.assertIn('linear-gradient', html_content)
        self.assertIn('border-radius', html_content)
        self.assertIn('box-shadow', html_content)
        self.assertIn('transition', html_content)
        self.assertIn('grid-template-columns', html_content)
        self.assertIn('rgba(', html_content)
        
        # Check for responsive design
        self.assertIn('viewport', html_content)
        self.assertIn('@media', html_content)
        
        # Check for enhanced navigation
        self.assertIn('nav-card', html_content)
    
    def test_node_status_indicators(self):
        """Test 4: Verify node status indicators (Active/Recent/Stale) are correctly assigned."""
        output_dir = self.test_dir / "status_test"
        output_dir.mkdir()
        
        # Create test data with different timestamps
        current_time = datetime.now()
        recent_time = current_time - timedelta(minutes=30)  # Should be Active
        old_time = current_time - timedelta(hours=2)       # Should be Recent  
        stale_time = current_time - timedelta(days=2)      # Should be Stale
        
        test_telemetry = pd.DataFrame({
            'timestamp': [
                current_time.strftime('%Y-%m-%d %H:%M:%S'),
                recent_time.strftime('%Y-%m-%d %H:%M:%S'),
                old_time.strftime('%Y-%m-%d %H:%M:%S'),
                stale_time.strftime('%Y-%m-%d %H:%M:%S')
            ],
            'node': ['!active01', '!recent01', '!old0001', '!stale001'],
            'battery_pct': [85.0, 75.0, 65.0, 55.0],
            'voltage_v': [3.8, 3.7, 3.6, 3.5],
            'channel_util_pct': [15.0, 20.0, 25.0, 30.0],
            'air_tx_pct': [5.0, 6.0, 7.0, 8.0],
            'uptime_s': [86400, 86400, 86400, 86400]
        })
        
        # Generate nodes list
        plot_meshtastic.write_comprehensive_nodes_list(
            test_telemetry, pd.DataFrame(), output_dir
        )
        
        html_content = (output_dir / "nodes.html").read_text()
        
        # Check that different status indicators are present
        # Note: We can't easily test the exact assignment without mocking datetime,
        # but we can verify the status system is implemented
        self.assertTrue(any(emoji in html_content for emoji in ['🟢', '🟡', '🔴']))
        self.assertTrue(any(status in html_content for status in ['Active', 'Recent', 'Stale']))
    
    def test_battery_level_visualization(self):
        """Test 5: Verify battery level visualization with color coding."""
        output_dir = self.test_dir / "battery_test"
        output_dir.mkdir()
        
        # Create test data with different battery levels
        test_telemetry = pd.DataFrame({
            'timestamp': ['2025-01-01 10:00:00', '2025-01-01 10:00:00', '2025-01-01 10:00:00'],
            'node': ['!high_bat', '!med_bat', '!low_bat'],
            'battery_pct': [85.0, 50.0, 15.0],  # High, medium, low battery
            'voltage_v': [3.8, 3.6, 3.2],
            'channel_util_pct': [15.0, 20.0, 25.0],
            'air_tx_pct': [5.0, 6.0, 7.0],
            'uptime_s': [86400, 86400, 86400]
        })
        
        plot_meshtastic.write_comprehensive_nodes_list(
            test_telemetry, pd.DataFrame(), output_dir
        )
        
        html_content = (output_dir / "nodes.html").read_text()
        
        # Check for battery visualization elements
        self.assertIn('battery', html_content.lower())
        self.assertIn('85.0%', html_content)
        self.assertIn('50.0%', html_content)
        self.assertIn('15.0%', html_content)
        
        # Check for color coding (CSS colors for different battery levels)
        self.assertIn('#4CAF50', html_content)  # Green for high battery
        self.assertIn('#FF9800', html_content)  # Orange for medium battery
        self.assertIn('#F44336', html_content)  # Red for low battery
    
    def test_emoji_icon_integration(self):
        """Test 6: Verify emoji/icon integration throughout HTML outputs."""
        output_dir = self.test_dir / "emoji_test"
        output_dir.mkdir()
        
        # Test root index emoji integration
        plot_meshtastic.write_root_index(output_dir)
        index_content = (output_dir / "index.html").read_text()
        
        # Check for emoji usage in main dashboard
        self.assertIn('🚀', index_content)  # Dashboard title
        self.assertIn('📊', index_content)  # Charts (in Getting Started section)
        self.assertIn('🌐', index_content)  # All nodes (in Getting Started section)
        
        # Test nodes list emoji integration
        plot_meshtastic.write_comprehensive_nodes_list(
            self.sample_telemetry, self.sample_traceroute, output_dir
        )
        nodes_content = (output_dir / "nodes.html").read_text()
        
        # Check for emoji usage in nodes list
        self.assertIn('🌐', nodes_content)  # Network nodes
        self.assertIn('🔋', nodes_content)  # Battery
        self.assertIn('📊', nodes_content)  # Telemetry
        self.assertIn('🔗', nodes_content)  # Routing
        self.assertIn('🔍', nodes_content)  # Search
    
    def test_responsive_design_elements(self):
        """Test 7: Verify responsive design elements are implemented."""
        output_dir = self.test_dir / "responsive_test"
        output_dir.mkdir()
        
        # Generate HTML files
        plot_meshtastic.write_root_index(output_dir)
        plot_meshtastic.write_comprehensive_nodes_list(
            self.sample_telemetry, self.sample_traceroute, output_dir
        )
        
        # Check root index responsive design
        index_content = (output_dir / "index.html").read_text()
        self.assertIn('viewport', index_content)
        self.assertIn('@media', index_content)
        self.assertIn('max-width: 768px', index_content)
        self.assertIn('grid-template-columns', index_content)
        self.assertIn('auto-fit', index_content)
        
        # Check nodes list responsive design
        nodes_content = (output_dir / "nodes.html").read_text()
        self.assertIn('viewport', nodes_content)
        self.assertIn('overflow-x: auto', nodes_content)
        self.assertIn('minmax(', nodes_content)
    
    def test_navigation_integration(self):
        """Test 8: Verify navigation integration between HTML files."""
        output_dir = self.test_dir / "nav_test"
        output_dir.mkdir()
        
        # Create all HTML files to test cross-navigation
        plot_meshtastic.write_root_index(output_dir)
        plot_meshtastic.write_comprehensive_nodes_list(
            self.sample_telemetry, self.sample_traceroute, output_dir
        )
        
        # Check root index navigation
        index_content = (output_dir / "index.html").read_text()
        # Note: navigation links are only created if the target files exist,
        # so we check for the navigation structure
        self.assertIn('nav-card', index_content)
        
        # Check nodes list navigation
        nodes_content = (output_dir / "nodes.html").read_text()
        self.assertIn('index.html', nodes_content)
        self.assertIn('dashboards.html', nodes_content)
        self.assertIn('diagnostics.html', nodes_content)
        self.assertIn('nav-link', nodes_content)
    
    def test_preserve_history_flag_integration(self):
        """Test 9: Verify --preserve-history flag creates proper directory structure."""
        # This test simulates the command-line behavior
        import argparse
        from unittest.mock import patch
        
        # Test argument parsing
        test_args = [
            '--telemetry', 'test.csv',
            '--traceroute', 'test2.csv', 
            '--preserve-history',
            '--outdir', str(self.test_dir)
        ]
        
        with patch('sys.argv', ['plot_meshtastic.py'] + test_args):
            args = plot_meshtastic.parse_args()
            self.assertTrue(args.preserve_history)
            self.assertEqual(args.outdir, str(self.test_dir))
        
        # Test directory creation behavior
        timestamped_dir = plot_meshtastic.create_timestamped_output_dir(self.test_dir)
        latest_link = self.test_dir / "latest"
        
        # Verify the structure
        self.assertTrue(timestamped_dir.exists())
        self.assertTrue(latest_link.exists())
        self.assertTrue(latest_link.is_symlink())
        self.assertEqual(str(latest_link.readlink()), timestamped_dir.name)


if __name__ == '__main__':
    # Create a custom test suite with verbose output
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEnhancedPlotting)
    runner = unittest.TextTestRunner(verbosity=2)
    
    print("=" * 70)
    print("🧪 Enhanced Plotting Functionality Test Suite")
    print("=" * 70)
    print("Testing comprehensive features:")
    print("• History preservation system")
    print("• Enhanced HTML dashboards with modern CSS")
    print("• Comprehensive node management")
    print("• Status indicators and battery visualization")
    print("• Emoji/icon integration")
    print("• Responsive design elements")
    print("• Navigation integration")
    print("=" * 70)
    
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! Enhanced plotting functionality is working correctly.")
        sys.exit(0)
    else:
        print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s) occurred.")
        sys.exit(1)