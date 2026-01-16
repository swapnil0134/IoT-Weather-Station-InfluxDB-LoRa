"""Main application for the weather monitoring system."""

import sys
import os
import time
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import ConfigManager
from src.radio import LoRaReceiver
from src.database import InfluxDBManager
from src.processing import DataProcessor


class WeatherMonitorApp:
    """Main weather monitoring application."""
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the weather monitoring application.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config: Optional[ConfigManager] = None
        self.lora_receiver: Optional[LoRaReceiver] = None
        self.influxdb_manager: Optional[InfluxDBManager] = None
        self.data_processor: Optional[DataProcessor] = None
        self.logger: Optional[logging.Logger] = None
        self.running = False
        
        self._initialize(config_path)
    
    def _initialize(self, config_path: Optional[str] = None) -> None:
        """Initialize all components."""
        try:
            # Load configuration
            self.config = ConfigManager(config_path)
            
            # Setup logging
            self._setup_logging()
            self.logger = logging.getLogger(__name__)
            
            # Initialize components
            self.data_processor = DataProcessor(self.config)
            self.influxdb_manager = InfluxDBManager(self.config)
            self.lora_receiver = LoRaReceiver(self.config)
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            self.logger.info("Weather monitoring system initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize weather monitoring system: {e}")
            sys.exit(1)
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_config = self.config.get_logging_config()
        
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('weather_monitor.log')
            ]
        )
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _save_to_file(self, timestamp: datetime, device_id: str, data: dict) -> bool:
        """Save data to daily log file."""
        try:
            storage_config = self.config.get_storage_config()
            log_base_dir = storage_config['log_base_dir']
            daily_log_file = storage_config['daily_log_file']
            
            # Create daily log folder
            today = timestamp.strftime("%Y-%m-%d")
            log_dir = os.path.join(log_base_dir, today)
            os.makedirs(log_dir, exist_ok=True)
            
            # Save to file
            log_file_path = os.path.join(log_dir, daily_log_file)
            formatted_message = self.data_processor.format_for_logging(timestamp, device_id, data)
            
            with open(log_file_path, 'a') as f:
                f.write(formatted_message + '\n')
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to save data to file: {e}")
            return False
    
    def _process_received_message(self, message: str) -> bool:
        """Process a received message and store it."""
        try:
            device_config = self.config.get_device_config()
            device_id = device_config['id']
            
            # Process and validate data
            timestamp, processed_data = self.data_processor.process_message(message, device_id)
            
            # Save to file
            file_success = self._save_to_file(timestamp, device_id, processed_data)
            
            # Save to InfluxDB
            db_success = self.influxdb_manager.write_sensor_data(timestamp, device_id, processed_data)
            
            # Log statistics
            stats = self.data_processor.get_field_statistics(processed_data)
            self.logger.info(f"Processed message: {stats}")
            
            return file_success and db_success
            
        except Exception as e:
            self.logger.error(f"Failed to process message: {e}")
            return False
    
    def run_single_cycle(self) -> bool:
        """Run a single cycle of handshake and receive."""
        try:
            device_config = self.config.get_device_config()
            device_id = device_config['id']
            
            # Send handshake
            if not self.lora_receiver.send_handshake():
                self.logger.warning("Failed to send handshake message")
                return False
            
            # Wait for response
            time.sleep(1)
            
            # Listen for device message
            message = self.lora_receiver.listen_for_device(device_id)
            
            if message:
                return self._process_received_message(message)
            else:
                self.logger.info("No message received from device")
                return False
                
        except Exception as e:
            self.logger.error(f"Error in single cycle: {e}")
            return False
    
    def run_continuous(self, interval: int = 300) -> None:
        """Run continuous monitoring with specified interval.
        
        Args:
            interval: Monitoring interval in seconds (default: 5 minutes)
        """
        self.logger.info(f"Starting continuous monitoring with {interval}s interval")
        self.running = True
        
        while self.running:
            try:
                start_time = time.time()
                
                # Run monitoring cycle
                success = self.run_single_cycle()
                
                if success:
                    self.logger.info("Monitoring cycle completed successfully")
                else:
                    self.logger.warning("Monitoring cycle completed with issues")
                
                # Calculate remaining sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                if sleep_time > 0 and self.running:
                    self.logger.debug(f"Sleeping for {sleep_time:.1f} seconds")
                    time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in continuous mode: {e}")
                if self.running:
                    time.sleep(10)  # Brief pause before retrying
        
        self.logger.info("Continuous monitoring stopped")
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up resources...")
        
        if self.influxdb_manager:
            self.influxdb_manager.close()
        
        self.logger.info("Weather monitoring system shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Weather Monitoring System')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--single', '-s', action='store_true', 
                       help='Run single monitoring cycle instead of continuous')
    parser.add_argument('--interval', '-i', type=int, default=300,
                       help='Monitoring interval in seconds for continuous mode (default: 300)')
    
    args = parser.parse_args()
    
    try:
        with WeatherMonitorApp(args.config) as app:
            if args.single:
                success = app.run_single_cycle()
                sys.exit(0 if success else 1)
            else:
                app.run_continuous(args.interval)
    
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()