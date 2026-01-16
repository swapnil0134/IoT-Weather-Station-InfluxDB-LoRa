"""InfluxDB client for storing sensor data."""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException

from ..config.config_manager import ConfigManager


class InfluxDBError(Exception):
    """Raised when InfluxDB operations fail."""
    pass


class InfluxDBManager:
    """Manages InfluxDB operations for sensor data storage."""
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize InfluxDB manager with configuration.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.retry_config = config.get_retry_config()
        
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize InfluxDB client with retry logic."""
        influxdb_config = self.config.get_influxdb_config()
        
        try:
            self.client = InfluxDBClient(
                url=influxdb_config['url'],
                token=influxdb_config['token'],
                org=influxdb_config['org']
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                self.logger.info("InfluxDB connection established successfully")
            else:
                raise InfluxDBError(f"InfluxDB health check failed: {health.message}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize InfluxDB client: {e}")
            raise InfluxDBError(f"InfluxDB initialization failed: {e}")
    
    def write_sensor_data(self, timestamp: datetime, device_id: str, data: Dict[str, Any]) -> bool:
        """Write sensor data to InfluxDB with retry logic.
        
        Args:
            timestamp: Data timestamp
            device_id: Device identifier
            data: Sensor data dictionary
            
        Returns:
            True if write was successful, False otherwise
        """
        if not self.write_api:
            self.logger.error("InfluxDB write API not initialized")
            return False
        
        return self._write_with_retry(timestamp, device_id, data)
    
    def _write_with_retry(self, timestamp: datetime, device_id: str, data: Dict[str, Any]) -> bool:
        """Write data with exponential backoff retry logic.
        
        Args:
            timestamp: Data timestamp
            device_id: Device identifier
            data: Sensor data dictionary
            
        Returns:
            True if write was successful, False otherwise
        """
        max_attempts = self.retry_config.get('max_attempts', 3)
        backoff_factor = self.retry_config.get('backoff_factor', 2)
        initial_delay = self.retry_config.get('initial_delay', 1.0)
        
        for attempt in range(max_attempts):
            try:
                # Create InfluxDB point
                point = self._create_point(timestamp, device_id, data)
                
                # Write to database
                influxdb_config = self.config.get_influxdb_config()
                self.write_api.write(
                    bucket=influxdb_config['bucket'],
                    org=influxdb_config['org'],
                    record=point
                )
                
                self.logger.debug(f"Successfully wrote data for {device_id} to InfluxDB")
                return True
                
            except ApiException as e:
                self.logger.warning(f"InfluxDB API error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                self.logger.warning(f"Unexpected error writing to InfluxDB on attempt {attempt + 1}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < max_attempts - 1:
                delay = initial_delay * (backoff_factor ** attempt)
                self.logger.info(f"Retrying InfluxDB write in {delay:.1f} seconds...")
                time.sleep(delay)
        
        self.logger.error(f"Failed to write data to InfluxDB after {max_attempts} attempts")
        return False
    
    def _create_point(self, timestamp: datetime, device_id: str, data: Dict[str, Any]) -> Point:
        """Create an InfluxDB Point from sensor data.
        
        Args:
            timestamp: Data timestamp
            device_id: Device identifier
            data: Sensor data dictionary
            
        Returns:
            InfluxDB Point object
        """
        point = Point("sensor_data").tag("device", device_id).time(timestamp, WritePrecision.S)
        
        for field_name, value in data.items():
            if isinstance(value, (int, float)):
                point.field(field_name, float(value))
            else:
                point.field(field_name, str(value))
        
        return point
    
    def test_connection(self) -> bool:
        """Test InfluxDB connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.client:
                return False
                
            health = self.client.health()
            return health.status == "pass"
            
        except Exception as e:
            self.logger.error(f"InfluxDB connection test failed: {e}")
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the InfluxDB database.
        
        Returns:
            Dictionary with database information
        """
        try:
            if not self.client:
                return {"status": "not_connected"}
            
            health = self.client.health()
            influxdb_config = self.config.get_influxdb_config()
            
            return {
                "status": health.status,
                "message": health.message,
                "url": influxdb_config['url'],
                "org": influxdb_config['org'],
                "bucket": influxdb_config['bucket']
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return {"status": "error", "message": str(e)}
    
    def close(self) -> None:
        """Close InfluxDB client connection."""
        try:
            if self.client:
                self.client.close()
                self.logger.info("InfluxDB connection closed")
        except Exception as e:
            self.logger.error(f"Error closing InfluxDB connection: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()