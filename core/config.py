#!/usr/bin/env python3
"""
Configuration management for Meshtastic logger.
"""
import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class LoggerConfig:
    """Configuration class for Meshtastic logger."""
    
    # Connection settings
    serial_device: Optional[str] = None
    timeout: int = 30
    retries: int = 3
    
    # Output settings
    telemetry_csv: str = "telemetry.csv"
    traceroute_csv: str = "traceroute.csv"
    plot_output_dir: str = "plots"
    
    # Execution settings
    interval: float = 300.0
    run_once: bool = False
    
    # Feature flags
    enable_traceroute: bool = True
    enable_plotting: bool = False
    regenerate_charts: bool = False
    
    # Node selection
    target_nodes: List[str] = field(default_factory=list)
    discover_all_nodes: bool = False
    
    @classmethod
    def from_env(cls) -> 'LoggerConfig':
        """Create configuration from environment variables."""
        return cls(
            serial_device=os.getenv('MESHTASTIC_SERIAL'),
            timeout=int(os.getenv('MESHTASTIC_TIMEOUT', '30')),
            retries=int(os.getenv('MESHTASTIC_RETRIES', '3')),
            telemetry_csv=os.getenv('TELEMETRY_CSV', 'telemetry.csv'),
            traceroute_csv=os.getenv('TRACEROUTE_CSV', 'traceroute.csv'),
            plot_output_dir=os.getenv('PLOT_OUTPUT_DIR', 'plots'),
            interval=float(os.getenv('LOGGER_INTERVAL', '300')),
            run_once=os.getenv('LOGGER_RUN_ONCE', '').lower() in ('true', '1', 'yes'),
            enable_traceroute=os.getenv('ENABLE_TRACEROUTE', '').lower() not in ('false', '0', 'no'),
            enable_plotting=os.getenv('ENABLE_PLOTTING', '').lower() in ('true', '1', 'yes'),
            regenerate_charts=os.getenv('REGENERATE_CHARTS', '').lower() in ('true', '1', 'yes'),
            discover_all_nodes=os.getenv('DISCOVER_ALL_NODES', '').lower() in ('true', '1', 'yes')
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.discover_all_nodes and not self.target_nodes:
            errors.append("Must specify either target_nodes or enable discover_all_nodes")
        
        if self.interval <= 0:
            errors.append("Interval must be positive")
        
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        
        if self.retries < 0:
            errors.append("Retries must be non-negative")
            
        # Validate output paths
        try:
            Path(self.plot_output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create plot output directory: {e}")
        
        return errors
    
    def get_telemetry_path(self) -> Path:
        """Get Path object for telemetry CSV."""
        return Path(self.telemetry_csv)
    
    def get_traceroute_path(self) -> Path:
        """Get Path object for traceroute CSV."""
        return Path(self.traceroute_csv)
    
    def get_plot_dir(self) -> Path:
        """Get Path object for plot output directory."""
        return Path(self.plot_output_dir)


# Default configuration instance
DEFAULT_CONFIG = LoggerConfig()