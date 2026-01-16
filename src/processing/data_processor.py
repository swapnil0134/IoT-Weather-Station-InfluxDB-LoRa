"""Data processor for sensor validation and transformation."""

import re
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from ..config.config_manager import ConfigManager


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataProcessor:
    """Processes and validates sensor data from LoRa devices."""
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize data processor with configuration.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.field_mappings = config.get_data_processing_config().get('field_mappings', {})
        self.validation_config = config.get_data_processing_config().get('validation', {})
        
    def process_message(self, message: str, device_id: str) -> Tuple[datetime, Dict[str, Any]]:
        """Process raw LoRa message and extract sensor data.
        
        Args:
            message: Raw message from LoRa device
            device_id: Expected device ID
            
        Returns:
            Tuple of (timestamp, processed_data_dict)
            
        Raises:
            DataValidationError: If message format is invalid or data is out of range
        """
        self.logger.debug(f"Processing message from {device_id}: {message}")
        
        # Validate message format
        if not self._validate_message_format(message, device_id):
            raise DataValidationError(f"Invalid message format or device ID mismatch: {message}")
        
        # Extract data fields
        raw_data = self._extract_data_fields(message)
        
        # Validate and transform data
        processed_data = self._validate_and_transform_data(raw_data)
        
        # Generate timestamp
        timestamp = datetime.utcnow()
        
        self.logger.info(f"Successfully processed message from {device_id}")
        return timestamp, processed_data
    
    def _validate_message_format(self, message: str, expected_device_id: str) -> bool:
        """Validate basic message format and device ID.
        
        Args:
            message: Raw message to validate
            expected_device_id: Expected device ID
            
        Returns:
            True if message format is valid
        """
        if not message or not isinstance(message, str):
            self.logger.warning("Empty or invalid message format")
            return False
        
        # Check if message contains expected device ID
        if expected_device_id not in message:
            self.logger.warning(f"Message does not contain expected device ID {expected_device_id}")
            return False
        
        # Basic pattern matching for data format (ID:DeviceX, field1:value1, field2:value2,...)
        pattern = rf'ID:{expected_device_id}(?:,\s*[\w_]+:[\w.+-]+)+'
        if not re.match(pattern, message.strip()):
            self.logger.warning(f"Message format does not match expected pattern: {message}")
            return False
        
        return True
    
    def _extract_data_fields(self, message: str) -> Dict[str, str]:
        """Extract data fields from message.
        
        Args:
            message: Raw message containing field data
            
        Returns:
            Dictionary of field names to string values
        """
        # Remove device ID prefix
        message = re.sub(r'ID:\w+,?\s*', '', message)
        
        # Split into field:value pairs
        field_pairs = [pair.strip() for pair in message.split(',')]
        
        data = {}
        for pair in field_pairs:
            if ':' in pair:
                field, value = pair.split(':', 1)
                data[field.strip()] = value.strip()
        
        return data
    
    def _validate_and_transform_data(self, raw_data: Dict[str, str]) -> Dict[str, Any]:
        """Validate data ranges and transform field names.
        
        Args:
            raw_data: Raw field data as strings
            
        Returns:
            Validated and transformed data dictionary
            
        Raises:
            DataValidationError: If validation fails
        """
        processed_data = {}
        
        for field_name, value in raw_data.items():
            # Apply field name mappings
            mapped_name = self.field_mappings.get(field_name, field_name)
            
            # Validate and convert value
            validated_value = self._validate_field_value(mapped_name, value)
            processed_data[mapped_name] = validated_value
        
        return processed_data
    
    def _validate_field_value(self, field_name: str, value: str) -> Any:
        """Validate individual field value against configured ranges.
        
        Args:
            field_name: Name of the field
            value: String value to validate
            
        Returns:
            Converted and validated value
            
        Raises:
            DataValidationError: If value is out of valid range
        """
        # Try to convert to float for numeric fields
        try:
            numeric_value = float(value)
        except ValueError:
            # Keep as string if not numeric
            return value
        
        # Check validation ranges if configured
        if field_name in self.validation_config:
            range_config = self.validation_config[field_name]
            min_val = range_config.get('min')
            max_val = range_config.get('max')
            
            if min_val is not None and numeric_value < min_val:
                self.logger.warning(f"Value {numeric_value} for {field_name} below minimum {min_val}")
                raise DataValidationError(f"{field_name} value {numeric_value} below minimum {min_val}")
            
            if max_val is not None and numeric_value > max_val:
                self.logger.warning(f"Value {numeric_value} for {field_name} above maximum {max_val}")
                raise DataValidationError(f"{field_name} value {numeric_value} above maximum {max_val}")
        
        return numeric_value
    
    def format_for_logging(self, timestamp: datetime, device_id: str, data: Dict[str, Any]) -> str:
        """Format processed data for logging.
        
        Args:
            timestamp: Message timestamp
            device_id: Device identifier
            data: Processed sensor data
            
        Returns:
            Formatted log string
        """
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        data_str = ", ".join([f"{k}:{v}" for k, v in data.items()])
        return f"[{timestamp_str}] ID:{device_id}, {data_str}"
    
    def get_field_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic statistics for the processed data.
        
        Args:
            data: Processed sensor data
            
        Returns:
            Dictionary with basic statistics
        """
        numeric_fields = {k: v for k, v in data.items() if isinstance(v, (int, float))}
        
        if not numeric_fields:
            return {"numeric_fields": 0}
        
        stats = {
            "total_fields": len(data),
            "numeric_fields": len(numeric_fields),
            "field_names": list(data.keys())
        }
        
        return stats