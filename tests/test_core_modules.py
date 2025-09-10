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
from core.telemetry import _collect_direct_telemetry


class TestCliUtils(unittest.TestCase):
    """Test CLI utility functions."""
    
    def test_validate_node_id(self):
        """Test node ID validation."""
        # Valid node IDs - hex format
        self.assertTrue(validate_node_id("abc123"))
        self.assertTrue(validate_node_id("!abc123"))
        self.assertTrue(validate_node_id("ABC123"))
        self.assertTrue(validate_node_id("123abc"))
        self.assertTrue(validate_node_id("ba4bf9d0"))
        self.assertTrue(validate_node_id("!ba4bf9d0"))
        
        # Valid node IDs - decimal format
        self.assertTrue(validate_node_id("1828779180"))
        self.assertTrue(validate_node_id("!1828779180"))
        self.assertTrue(validate_node_id("123456"))
        
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


class TestTelemetry(unittest.TestCase):
    """Test telemetry functions."""
    
    def test_telemetry_command_format(self):
        """Test that telemetry uses correct --request-telemetry --dest format."""
        from unittest.mock import patch, MagicMock
        
        # Mock the run_cli function to capture the command used
        with patch('core.telemetry.run_cli') as mock_run_cli:
            mock_run_cli.return_value = (True, "Battery level: 85%\nVoltage: 3.2V")
            
            # Test hex format node ID  
            _collect_direct_telemetry("!ba4bf9d0")
            
            # Verify the command format (should try multiple sensor types)
            # Check that at least one call was made with the basic telemetry request
            calls = [call[0][0] for call in mock_run_cli.call_args_list]
            
            # Should have calls for different sensor types, including the basic one
            basic_command = ["meshtastic", "--request-telemetry", "--dest", "!ba4bf9d0"]
            sensor_command_pattern = ["meshtastic", "--request-telemetry"]  # + sensor type + --dest + node
            
            # Check that we made multiple telemetry requests (enhanced collection)
            self.assertTrue(len(calls) > 1, "Should make multiple telemetry requests for different sensor types")
            
            # Check that the basic command format is used somewhere in the calls
            basic_found = any(call == basic_command for call in calls)
            self.assertTrue(basic_found, f"Should include basic telemetry command, got calls: {calls}")
            
            # Test decimal format node ID
            # Clear previous call history
            mock_run_cli.reset_mock()
            _collect_direct_telemetry("1828779180")
            
            # Verify the command format for decimal (should also make multiple calls)
            calls = [call[0][0] for call in mock_run_cli.call_args_list]
            
            # Check that we made multiple telemetry requests for this node too
            self.assertTrue(len(calls) > 1, "Should make multiple telemetry requests for decimal node ID too")
            
            # Check that the basic decimal command format is used somewhere
            basic_decimal_command = ["meshtastic", "--request-telemetry", "--dest", "1828779180"]
            basic_decimal_found = any(call == basic_decimal_command for call in calls)
            self.assertTrue(basic_decimal_found, f"Should include basic telemetry command for decimal ID, got calls: {calls}")


class TestNodeDiscovery(unittest.TestCase):
    """Test node discovery functions."""
    
    def test_normalize_node_id(self):
        """Test node ID normalization."""
        self.assertEqual(normalize_node_id("abc123"), "!abc123")
        self.assertEqual(normalize_node_id("!abc123"), "!abc123")
        self.assertEqual(normalize_node_id(""), "")


if __name__ == '__main__':
    unittest.main()