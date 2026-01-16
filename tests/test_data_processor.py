"""Tests for data processor."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.processing.data_processor import DataProcessor, DataValidationError
from src.config.config_manager import ConfigManager


class TestDataProcessor:
    """Test cases for DataProcessor."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=ConfigManager)
        config.get_data_processing_config.return_value = {
            'field_mappings': {
                'Max_A': 'maxAcceleration_m/s2',
                'RMS_A': 'rmsAcceleration_m/s2',
                'Temp': 'temperature_C',
                'Pressure': 'pressure_hPa',
                'Humidity': 'humidity_%'
            },
            'validation': {
                'temperature': {'min': -40.0, 'max': 85.0},
                'pressure': {'min': 300.0, 'max': 1100.0},
                'humidity': {'min': 0.0, 'max': 100.0},
                'acceleration': {'min': 0.0, 'max': 100.0}
            }
        }
        return config
    
    @pytest.fixture
    def data_processor(self, mock_config):
        """Create a DataProcessor instance with mock config."""
        return DataProcessor(mock_config)
    
    def test_process_message_success(self, data_processor):
        """Test successful message processing."""
        message = "ID:Device5, Max_A:2.50, RMS_A:1.80, Temp:25.5, Pressure:1013.25, Humidity:65.0"
        device_id = "Device5"
        
        timestamp, processed_data = data_processor.process_message(message, device_id)
        
        assert isinstance(timestamp, datetime)
        assert 'maxAcceleration_m/s2' in processed_data
        assert 'rmsAcceleration_m/s2' in processed_data
        assert 'temperature_C' in processed_data
        assert 'pressure_hPa' in processed_data
        assert 'humidity_%' in processed_data
        
        assert processed_data['maxAcceleration_m/s2'] == 2.5
        assert processed_data['temperature_C'] == 25.5
    
    def test_process_message_invalid_device_id(self, data_processor):
        """Test processing message with wrong device ID."""
        message = "ID:Device4, Max_A:2.50, Temp:25.5"
        device_id = "Device5"
        
        with pytest.raises(DataValidationError, match="Invalid message format or device ID mismatch"):
            data_processor.process_message(message, device_id)
    
    def test_process_message_empty_message(self, data_processor):
        """Test processing empty message."""
        message = ""
        device_id = "Device5"
        
        with pytest.raises(DataValidationError):
            data_processor.process_message(message, device_id)
    
    def test_process_message_invalid_format(self, data_processor):
        """Test processing message with invalid format."""
        message = "Invalid format without proper structure"
        device_id = "Device5"
        
        with pytest.raises(DataValidationError):
            data_processor.process_message(message, device_id)
    
    def test_validate_field_value_temperature_ok(self, data_processor):
        """Test valid temperature validation."""
        result = data_processor._validate_field_value('temperature_C', '25.5')
        assert result == 25.5
    
    def test_validate_field_value_temperature_too_low(self, data_processor):
        """Test temperature validation - too low."""
        with pytest.raises(DataValidationError, match="temperature_C value .* below minimum"):
            data_processor._validate_field_value('temperature_C', '-50.0')
    
    def test_validate_field_value_temperature_too_high(self, data_processor):
        """Test temperature validation - too high."""
        with pytest.raises(DataValidationError, match="temperature_C value .* above maximum"):
            data_processor._validate_field_value('temperature_C', '100.0')
    
    def test_validate_field_value_non_numeric(self, data_processor):
        """Test validation of non-numeric field."""
        result = data_processor._validate_field_value('unknown_field', 'string_value')
        assert result == 'string_value'
    
    def test_format_for_logging(self, data_processor):
        """Test formatting data for logging."""
        timestamp = datetime(2024, 1, 15, 10, 30, 45)
        device_id = "Device5"
        data = {
            'maxAcceleration_m/s2': 2.5,
            'temperature_C': 25.5,
            'pressure_hPa': 1013.25
        }
        
        result = data_processor.format_for_logging(timestamp, device_id, data)
        
        assert 'ID:Device5' in result
        assert 'maxAcceleration_m/s2:2.5' in result
        assert 'temperature_C:25.5' in result
        assert '2024-01-15T10:30:45' in result
    
    def test_get_field_statistics(self, data_processor):
        """Test generating field statistics."""
        data = {
            'maxAcceleration_m/s2': 2.5,
            'temperature_C': 25.5,
            'status': 'OK'  # String field
        }
        
        stats = data_processor.get_field_statistics(data)
        
        assert stats['total_fields'] == 3
        assert stats['numeric_fields'] == 2
        assert 'maxAcceleration_m/s2' in stats['field_names']
        assert 'temperature_C' in stats['field_names']
        assert 'status' in stats['field_names']
    
    def test_get_field_statistics_no_numeric(self, data_processor):
        """Test generating statistics with no numeric fields."""
        data = {
            'status': 'OK',
            'device_type': 'sensor'
        }
        
        stats = data_processor.get_field_statistics(data)
        
        assert stats['numeric_fields'] == 0
        assert stats['total_fields'] == 2
    
    def test_extract_data_fields(self, data_processor):
        """Test extracting data fields from message."""
        message = "Max_A:2.50, RMS_A:1.80, Temp:25.5"
        
        data = data_processor._extract_data_fields(message)
        
        assert data['Max_A'] == '2.50'
        assert data['RMS_A'] == '1.80'
        assert data['Temp'] == '25.5'
    
    def test_validate_and_transform_data(self, data_processor):
        """Test data validation and transformation."""
        raw_data = {
            'Max_A': '2.50',
            'Temp': '25.5',
            'Status': 'OK'
        }
        
        processed = data_processor._validate_and_transform_data(raw_data)
        
        assert 'maxAcceleration_m/s2' in processed
        assert 'temperature_C' in processed
        assert 'Status' in processed  # Unmapped field keeps original name
        
        assert processed['maxAcceleration_m/s2'] == 2.5
        assert processed['temperature_C'] == 25.5
        assert processed['Status'] == 'OK'