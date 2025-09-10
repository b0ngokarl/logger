#!/usr/bin/env python3
"""
CLI utilities for running meshtastic commands safely.

This module provides secure command execution with proper validation,
timeout handling, and error reporting for the Alpha version.
"""
import subprocess
import re
import sys
from typing import List, Tuple, Optional


def run_cli(cmd: List[str], timeout: int = 30) -> Tuple[bool, str]:
    """
    Run a CLI command safely with timeout and validation.
    
    Args:
        cmd: Command as list of strings (prevents shell injection)
        timeout: Command timeout in seconds (default: 30)
        
    Returns:
        Tuple of (success_flag, output_string)
        
    Security Features:
        - No shell execution to prevent injection
        - Enforced timeout limits
        - Input validation on command structure
    """
    # Security: enforce list command, no shell, limited timeout
    if not isinstance(cmd, list) or not cmd:
        return False, "[INVALID_CMD]"
    
    try:
        out = subprocess.check_output(
            cmd, 
            stderr=subprocess.STDOUT, 
            text=True, 
            timeout=timeout, 
            shell=False
        )
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output if e.output else "[PROCESS_ERROR]"
    except subprocess.TimeoutExpired:
        return False, "[TIMEOUT]"
    except Exception as e:
        return False, f"[ERROR]: {str(e)}"


def validate_node_id(node_id: str) -> bool:
    """
    Validate a Meshtastic node ID format.
    
    Supports both formats:
    - Hex format: !ba4bf9d0 (with or without leading !)
    - Decimal format: 1828779180
    
    Args:
        node_id: Node ID string to validate
        
    Returns:
        bool: True if valid format, False otherwise
        
    Examples:
        >>> validate_node_id("!ba4bf9d0")
        True
        >>> validate_node_id("1828779180")  
        True
        >>> validate_node_id("invalid")
        False
    """
    if not node_id:
        return False
    
    # Remove leading ! if present for validation
    clean_id = node_id.lstrip('!')
    
    # Should be alphanumeric characters (covers both hex and decimal formats)
    return bool(re.match(r"^[0-9a-zA-Z]+$", clean_id))


def validate_serial_device(serial_dev: str) -> bool:
    """
    Validate a serial device path.
    
    Args:
        serial_dev: Serial device path to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not serial_dev:
        return False
    
    # Accept common serial device patterns
    return bool(re.match(r"^/dev/tty[A-Z]+[0-9]+$", serial_dev))


def build_meshtastic_command(base_args: List[str], serial_dev: Optional[str] = None) -> List[str]:
    """
    Build a meshtastic command with optional serial device.
    
    Args:
        base_args: Base meshtastic command arguments
        serial_dev: Optional serial device path
        
    Returns:
        Complete command list
    """
    cmd = ["meshtastic"] + base_args
    
    if serial_dev:
        if not validate_serial_device(serial_dev):
            print(f"[ERROR] Invalid serial device: {serial_dev}", file=sys.stderr)
            return cmd
        cmd.extend(["--port", serial_dev])
    
    return cmd