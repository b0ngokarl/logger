#!/usr/bin/env python3
"""
Unit tests for core modules.
"""
import unittest
import tempfile
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cli_utils import validate_node_id, validate_serial_device, build_meshtastic_command
from core.csv_utils import iso_now, ensure_header, append_row
from core.node_discovery import normalize_node_id


class TestCliUtils(unittest.TestCase):
    """Test CLI utility functions."""
    
    def test_validate_node_id(self):
        """Test node ID validation."""
        # Valid node IDs
        self.assertTrue(validate_node_id("abc123"))
        self.assertTrue(validate_node_id("!abc123"))
        self.assertTrue(validate_node_id("ABC123"))
        self.assertTrue(validate_node_id("123abc"))
        
        # Invalid node IDs
        self.assertFalse(validate_node_id(""))
        self.assertFalse(validate_node_id("ab-c"))
        self.assertFalse(validate_node_id("ab c"))
        self.assertFalse(validate_node_id("ab.c"))
    
    def test_validate_serial_device(self):
        """Test serial device validation."""
        # Valid serial devices
        self.assertTrue(validate_serial_device("/dev/ttyUSB0"))
        self.assertTrue(validate_serial_device("/dev/ttyACM0"))
        self.assertTrue(validate_serial_device("/dev/ttyAMA0"))
        
        # Invalid serial devices
        self.assertFalse(validate_serial_device(""))
        self.assertFalse(validate_serial_device("/dev/null"))
        self.assertFalse(validate_serial_device("ttyUSB0"))
        self.assertFalse(validate_serial_device("/dev/tty"))
    
    def test_build_meshtastic_command(self):
        """Test meshtastic command building."""
        # Basic command
        cmd = build_meshtastic_command(["--nodes"])
        self.assertEqual(cmd, ["meshtastic", "--nodes"])
        
        # Command with serial device
        cmd = build_meshtastic_command(["--nodes"], "/dev/ttyUSB0")
        self.assertEqual(cmd, ["meshtastic", "--nodes", "--port", "/dev/ttyUSB0"])
        
        # Command with invalid serial device (should not add port)
        cmd = build_meshtastic_command(["--nodes"], "invalid")
        self.assertEqual(cmd, ["meshtastic", "--nodes"])


class TestCsvUtils(unittest.TestCase):
    """Test CSV utility functions."""
    
    def test_iso_now(self):
        """Test ISO timestamp generation."""
        timestamp = iso_now()
        self.assertIsInstance(timestamp, str)
        self.assertRegex(timestamp, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
    
    def test_ensure_header(self):
        """Test CSV header creation."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            csv_path = Path(f.name)
        
        try:
            # Test with non-existent file
            ensure_header(csv_path, ["col1", "col2", "col3"])
            content = csv_path.read_text()
            self.assertEqual(content.strip(), "col1,col2,col3")
            
            # Test with existing file that has different header
            csv_path.write_text("old,header\ndata,row\n")
            ensure_header(csv_path, ["col1", "col2", "col3"])
            content = csv_path.read_text()
            self.assertTrue(content.startswith("col1,col2,col3"))
            
        finally:
            csv_path.unlink(missing_ok=True)
    
    def test_append_row(self):
        """Test CSV row appending."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            csv_path = Path(f.name)
        
        try:
            # Test appending rows
            append_row(csv_path, ["value1", "value2", 123])
            append_row(csv_path, ["value3", "value4", 456])
            
            content = csv_path.read_text()
            lines = content.strip().split('\n')
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0], "value1,value2,123")
            self.assertEqual(lines[1], "value3,value4,456")
            
        finally:
            csv_path.unlink(missing_ok=True)


class TestNodeDiscovery(unittest.TestCase):
    """Test node discovery functions."""
    
    def test_normalize_node_id(self):
        """Test node ID normalization."""
        self.assertEqual(normalize_node_id("abc123"), "!abc123")
        self.assertEqual(normalize_node_id("!abc123"), "!abc123")
        self.assertEqual(normalize_node_id(""), "")


if __name__ == '__main__':
    unittest.main()