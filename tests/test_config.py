"""Tests for configuration manager."""

import pytest
import tempfile
import os
import yaml
from unittest.mock import patch, mock_open

from src.config.config_manager import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager."""
    
    def test_load_config_success(self):
        """Test successful configuration loading."""
        config_data = {
            'lora': {'frequency_mhz': 868.0},
            'influxdb': {'token': 'test_token'},
            'device': {'id': 'Device5'},
            'logging': {'level': 'INFO'},
            'storage': {'log_base_dir': '/tmp/logs'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = ConfigManager(config_path)
            assert config.get('lora.frequency_mhz') == 868.0
            assert config.get('device.id') == 'Device5'
        finally:
            os.unlink(config_path)
    
    def test_config_file_not_found(self):
        """Test handling of missing configuration file."""
        with pytest.raises(FileNotFoundError):
            ConfigManager('/nonexistent/config.yaml')
    
    def test_env_override(self):
        """Test environment variable override."""
        config_data = {
            'lora': {'frequency_mhz': 868.0},
            'influxdb': {'token': 'original_token'},
            'device': {'id': 'Device5'},
            'logging': {'level': 'INFO'},
            'storage': {'log_base_dir': '/tmp/logs'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            with patch.dict(os.environ, {'INFLUXDB_TOKEN': 'override_token'}):
                config = ConfigManager(config_path)
                assert config.get('influxdb.token') == 'override_token'
        finally:
            os.unlink(config_path)
    
    def test_get_with_default(self):
        """Test getting configuration with default values."""
        config_data = {
            'lora': {'frequency_mhz': 868.0},
            'influxdb': {'token': 'test_token'},
            'device': {'id': 'Device5'},
            'logging': {'level': 'INFO'},
            'storage': {'log_base_dir': '/tmp/logs'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = ConfigManager(config_path)
            assert config.get('nonexistent.key', 'default') == 'default'
            assert config.get('lora.nonexistent', 123) == 123
        finally:
            os.unlink(config_path)
    
    def test_validation_missing_influxdb_token(self):
        """Test validation when InfluxDB token is missing."""
        config_data = {
            'lora': {'frequency_mhz': 868.0},
            'influxdb': {'token': ''},
            'device': {'id': 'Device5'},
            'logging': {'level': 'INFO'},
            'storage': {'log_base_dir': '/tmp/logs'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            with pytest.raises(ValueError, match="InfluxDB token must be set"):
                ConfigManager(config_path)
        finally:
            os.unlink(config_path)
    
    def test_get_specific_configs(self):
        """Test getting specific configuration sections."""
        config_data = {
            'lora': {'frequency_mhz': 868.0, 'tx_power': 23},
            'influxdb': {'token': 'test_token', 'url': 'http://localhost:8086'},
            'device': {'id': 'Device5', 'handshake_message': 'Device5'},
            'logging': {'level': 'INFO'},
            'storage': {'log_base_dir': '/tmp/logs'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config = ConfigManager(config_path)
            
            lora_config = config.get_lora_config()
            assert lora_config['frequency_mhz'] == 868.0
            assert lora_config['tx_power'] == 23
            
            influxdb_config = config.get_influxdb_config()
            assert influxdb_config['token'] == 'test_token'
            assert influxdb_config['url'] == 'http://localhost:8086'
            
            device_config = config.get_device_config()
            assert device_config['id'] == 'Device5'
            
        finally:
            os.unlink(config_path)