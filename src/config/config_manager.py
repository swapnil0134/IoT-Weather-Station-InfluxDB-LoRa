"""Configuration manager for the weather monitoring system."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, looks for config.yaml
                        in current directory and then package directory.
        """
        self._config_path = config_path or self._find_config_file()
        self._config: Dict[str, Any] = {}
        self._load_config()
        
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        possible_paths = [
            os.environ.get('CONFIG_PATH'),
            'config.yaml',
            os.path.join(os.path.dirname(__file__), '../../../config.yaml')
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                return os.path.abspath(path)
                
        raise FileNotFoundError(
            "Configuration file not found. Please create config.yaml or set CONFIG_PATH environment variable."
        )
    
    def _load_config(self) -> None:
        """Load configuration from YAML file and environment variables."""
        try:
            with open(self._config_path, 'r') as file:
                self._config = yaml.safe_load(file) or {}
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
        
        # Override with environment variables
        self._apply_env_overrides()
        
        # Validate configuration
        self._validate_config()
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        env_mappings = {
            'INFLUXDB_TOKEN': ['influxdb', 'token'],
            'INFLUXDB_URL': ['influxdb', 'url'],
            'INFLUXDB_ORG': ['influxdb', 'org'],
            'INFLUXDB_BUCKET': ['influxdb', 'bucket'],
            'DEVICE_ID': ['device', 'id'],
            'LOG_LEVEL': ['logging', 'level'],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                self._set_nested_value(config_path, value)
    
    def _set_nested_value(self, path: list, value: str) -> None:
        """Set nested configuration value."""
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _validate_config(self) -> None:
        """Validate required configuration values."""
        required_sections = ['lora', 'influxdb', 'device', 'logging', 'storage']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        # Validate critical values
        if not self._config['influxdb'].get('token'):
            if not os.environ.get('INFLUXDB_TOKEN'):
                raise ValueError("InfluxDB token must be set in config or INFLUXDB_TOKEN environment variable")
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            path: Configuration path using dot notation (e.g., 'lora.frequency_mhz')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        keys = path.split('.')
        current = self._config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def get_influxdb_config(self) -> Dict[str, Any]:
        """Get InfluxDB configuration."""
        return self._config['influxdb'].copy()
    
    def get_lora_config(self) -> Dict[str, Any]:
        """Get LoRa configuration."""
        return self._config['lora'].copy()
    
    def get_device_config(self) -> Dict[str, Any]:
        """Get device configuration."""
        return self._config['device'].copy()
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self._config['logging'].copy()
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return self._config['storage'].copy()
    
    def get_data_processing_config(self) -> Dict[str, Any]:
        """Get data processing configuration."""
        return self._config.get('data_processing', {})
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration."""
        return self._config.get('retry', {
            'max_attempts': 3,
            'backoff_factor': 2,
            'initial_delay': 1.0
        })
    
    @property
    def config_path(self) -> str:
        """Get path to configuration file."""
        return self._config_path