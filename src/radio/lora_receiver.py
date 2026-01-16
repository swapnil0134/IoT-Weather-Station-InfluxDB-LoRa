"""LoRa radio receiver for weather monitoring system."""

import time
import logging
from typing import Optional, Callable, Dict, Any

try:
    import board
    import busio
    import digitalio
    import adafruit_rfm9x
except ImportError as e:
    logging.warning(f"LoRa hardware libraries not available: {e}")
    # Create mock classes for testing
    board = None
    busio = None
    digitalio = None
    adafruit_rfm9x = None

from ..config.config_manager import ConfigManager


class LoRaError(Exception):
    """Raised when LoRa operations fail."""
    pass


class LoRaReceiver:
    """Manages LoRa radio communication for receiving sensor data."""
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize LoRa receiver with configuration.
        
        Args:
            config: Configuration manager instance
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.rfm9x: Optional[any] = None
        self._initialize_radio()
    
    def _initialize_radio(self) -> None:
        """Initialize LoRa radio with configuration parameters."""
        if not all([board, busio, digitalio, adafruit_rfm9x]):
            raise LoRaError("LoRa hardware libraries not available")
        
        try:
            lora_config = self.config.get_lora_config()
            pins_config = lora_config['pins']
            
            # Initialize SPI bus
            spi = busio.SPI(
                getattr(board, pins_config['sck']),
                MOSI=getattr(board, pins_config['mosi']),
                MISO=getattr(board, pins_config['miso'])
            )
            
            # Initialize pins
            cs = digitalio.DigitalInOut(getattr(board, pins_config['cs']))
            reset = digitalio.DigitalInOut(getattr(board, pins_config['reset']))
            
            # Initialize RFM radio
            self.rfm9x = adafruit_rfm9x.RFM9x(
                spi, cs, reset, 
                lora_config['frequency_mhz'],
                baudrate=lora_config['baudrate']
            )
            
            # Configure radio parameters
            self.rfm9x.tx_power = lora_config['tx_power']
            self.rfm9x.spreading_factor = lora_config['spreading_factor']
            
            self.logger.info("LoRa radio initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LoRa radio: {e}")
            raise LoRaError(f"LoRa radio initialization failed: {e}")
    
    def send_handshake(self, message: Optional[str] = None) -> bool:
        """Send handshake message to trigger device response.
        
        Args:
            message: Handshake message to send (uses config default if None)
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.rfm9x:
            self.logger.error("LoRa radio not initialized")
            return False
        
        try:
            device_config = self.config.get_device_config()
            handshake_msg = message or device_config.get('handshake_message', 'Device5')
            
            self.rfm9x.send(bytes(handshake_msg, "ascii"))
            self.logger.info(f"Handshake message sent: {handshake_msg}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send handshake message: {e}")
            return False
    
    def receive_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """Receive message from LoRa radio.
        
        Args:
            timeout: Receive timeout in seconds (uses config default if None)
            
        Returns:
            Received message as string, or None if no message received
        """
        if not self.rfm9x:
            self.logger.error("LoRa radio not initialized")
            return None
        
        try:
            device_config = self.config.get_device_config()
            receive_timeout = timeout or device_config.get('message_timeout', 10.0)
            
            packet = self.rfm9x.receive(timeout=receive_timeout, with_header=True)
            
            if packet is not None:
                # Decode to text
                message = str(packet, "latin-1")
                self.logger.debug(f"Received raw packet: {message}")
                return message
            else:
                self.logger.debug("No packet received within timeout")
                return None
                
        except Exception as e:
            self.logger.error(f"Error receiving message: {e}")
            return None
    
    def listen_for_device(self, device_id: str, timeout: Optional[float] = None, 
                         message_callback: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """Listen for messages from a specific device.
        
        Args:
            device_id: Device ID to listen for
            timeout: Listen timeout in seconds
            message_callback: Optional callback function for received messages
            
        Returns:
            Message from specified device, or None if timeout
        """
        start_time = time.time()
        device_config = self.config.get_device_config()
        listen_timeout = timeout or device_config.get('message_timeout', 10.0)
        
        self.logger.info(f"Listening for messages from {device_id}")
        
        while time.time() - start_time < listen_timeout:
            message = self.receive_message(timeout=1.0)  # Short timeout for responsive checking
            
            if message and device_id in message:
                self.logger.info(f"Received message from {device_id}: {message}")
                
                if message_callback:
                    message_callback(message)
                
                return message
        
        self.logger.info(f"No message received from {device_id} within timeout")
        return None
    
    def get_radio_status(self) -> Dict[str, Any]:
        """Get current radio status information.
        
        Returns:
            Dictionary with radio status information
        """
        if not self.rfm9x:
            return {"status": "not_initialized"}
        
        try:
            # Get available radio properties
            status = {
                "status": "initialized",
                "frequency_mhz": self.rfm9x.frequency_mhz,
                "tx_power": getattr(self.rfm9x, 'tx_power', 'unknown'),
                "spreading_factor": getattr(self.rfm9x, 'spreading_factor', 'unknown'),
                "rssi": getattr(self.rfm9x, 'rssi', 'unknown'),
                "snr": getattr(self.rfm9x, 'snr', 'unknown')
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting radio status: {e}")
            return {"status": "error", "message": str(e)}
    
    def test_radio(self) -> bool:
        """Test radio functionality.
        
        Returns:
            True if radio is working properly, False otherwise
        """
        try:
            if not self.rfm9x:
                return False
            
            # Try to get radio status
            status = self.get_radio_status()
            return status.get("status") == "initialized"
            
        except Exception as e:
            self.logger.error(f"Radio test failed: {e}")
            return False