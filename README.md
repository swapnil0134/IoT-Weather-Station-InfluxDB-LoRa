# Weather Monitoring System

A modular, robust LoRa-based weather monitoring system for Raspberry Pi that receives sensor data from remote weather stations and stores it in both log files and InfluxDB time-series database.

## Features

- **Modular Architecture**: Separated concerns into radio communication, data processing, and database storage
- **Robust Error Handling**: Comprehensive exception handling with retry logic
- **Input Validation**: Data range validation and sanitization
- **Secure Configuration**: External configuration with environment variable support
- **Comprehensive Logging**: Structured logging with multiple outputs
- **Type Safety**: Full type hints throughout the codebase
- **Testing**: Unit tests for core functionality
- **Hardware Abstraction**: Graceful handling when LoRa hardware is unavailable

## System Architecture

```
Weather_Monitoring/
├── config.yaml           # Main configuration file
├── .env.example          # Environment variables template
├── main.py               # Main application entry point
├── requirements.txt      # Python dependencies
├── src/
│   ├── config/          # Configuration management
│   ├── radio/           # LoRa radio communication
│   ├── database/        # InfluxDB operations
│   ├── processing/      # Data validation and transformation
│   └── __init__.py
├── tests/               # Unit tests
├── logs/               # Application logs
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Raspberry Pi with LoRa hardware (for production)
- InfluxDB instance (local or remote)
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Weather_Monitoring
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up configuration:**
   ```bash
   # Copy and edit configuration
   cp config.yaml.example config.yaml
   cp .env.example .env
   
   # Edit .env with your InfluxDB credentials
   nano .env
   ```

5. **Configure InfluxDB:**
   - Ensure InfluxDB is running and accessible
   - Create a bucket named `LoRa_Atmosphere`
   - Update `.env` with your InfluxDB token and connection details

### Running the System

#### Single Cycle Mode (Testing)
```bash
python main.py --single
```

#### Continuous Monitoring Mode (Production)
```bash
python main.py
# Custom interval (default: 5 minutes)
python main.py --interval 60
```

#### Custom Configuration
```bash
python main.py --config /path/to/config.yaml
```

## Configuration

### Main Configuration (config.yaml)

```yaml
# LoRa Radio Configuration
lora:
  frequency_mhz: 868.0
  baudrate: 100000
  tx_power: 23
  spreading_factor: 8
  pins:
    cs: "CE1"
    reset: "D25"
    sck: "SCK"
    mosi: "MOSI"
    miso: "MISO"

# InfluxDB Configuration
influxdb:
  url: "http://localhost:8086"
  org: "smdh"
  bucket: "LoRa_Atmosphere"
  token: ""  # Set via environment variable

# Device Configuration
device:
  id: "Device5"
  handshake_message: "Device5"
  message_timeout: 10.0

# Data Processing Configuration
data_processing:
  field_mappings:
    "Max_A": "maxAcceleration_m/s2"
    "RMS_A": "rmsAcceleration_m/s2"
    "Temp": "temperature_C"
    "Pressure": "pressure_hPa"
    "Humidity": "humidity_%"
  validation:
    temperature: {min: -40.0, max: 85.0}
    pressure: {min: 300.0, max: 1100.0}
    humidity: {min: 0.0, max: 100.0}
    acceleration: {min: 0.0, max: 100.0}
```

### Environment Variables (.env)

```bash
# Required
INFLUXDB_TOKEN=your_influxdb_token_here
INFLUXDB_URL=http://localhost:8086
INFLUXDB_ORG=smdh
INFLUXDB_BUCKET=LoRa_Atmosphere

# Optional
DEVICE_ID=Device5
LOG_LEVEL=INFO
CONFIG_PATH=/path/to/config.yaml
```

## Hardware Setup

### Raspberry Pi LoRa Configuration

1. **Connect LoRa Module:**
   - CE1 → Chip Select
   - D25 → Reset
   - SCK → SPI Clock
   - MOSI → SPI MOSI
   - MISO → SPI MISO

2. **Enable SPI:**
   ```bash
   sudo raspi-config
   # Navigate to Interface Options → SPI → Enable
   ```

3. **Install hardware libraries (production only):**
   ```bash
   pip install adafruit-circuitpython-rfm9x adafruit-circuitpython-board
   ```

## Message Format

The system expects messages in the following format:

```
ID:Device5, Max_A:2.50, RMS_A:1.80, Temp:25.5, Pressure:1013.25, Humidity:65.0
```

### Field Mappings

| Original | Mapped Field | Unit |
|----------|--------------|------|
| Max_A    | maxAcceleration_m/s2 | m/s² |
| RMS_A    | rmsAcceleration_m/s2 | m/s² |
| Temp     | temperature_C | °C |
| Pressure | pressure_hPa | hPa |
| Humidity | humidity_% | % |

## Data Storage

### File Logs
- **Location**: `/home/swapnil/LoRa_Devices/Weather_Monitoring/Logs/YYYY-MM-DD/log.txt`
- **Format**: `[timestamp] ID:DeviceX, field1:value1, field2:value2,...`

### InfluxDB
- **Measurement**: `sensor_data`
- **Tag**: `device=DeviceX`
- **Fields**: Mapped sensor data with proper units

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_config.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Devices

1. Update `config.yaml` with new device configuration
2. Add field mappings in `data_processing.field_mappings`
3. Add validation ranges if needed
4. Test with `python main.py --single`

### Extending Functionality

The modular architecture allows easy extension:

- **New Radio Types**: Add to `src/radio/`
- **New Databases**: Add to `src/database/`
- **New Processing Logic**: Add to `src/processing/`

## Troubleshooting

### Common Issues

1. **LoRa Hardware Not Found:**
   - Check SPI is enabled: `ls /dev/spi*`
   - Verify pin connections
   - Check hardware libraries are installed

2. **InfluxDB Connection Failed:**
   - Verify InfluxDB is running: `curl http://localhost:8086/health`
   - Check token and organization settings
   - Ensure bucket exists

3. **Configuration Errors:**
   - Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
   - Check environment variables are set correctly

4. **Permission Issues:**
   - Ensure write access to log directory
   - Check InfluxDB user permissions

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python main.py --single
```

## Performance Monitoring

### System Metrics

Monitor system performance with the built-in statistics:

```python
from src.processing import DataProcessor
# Statistics are logged automatically for each processed message
```

### Database Health

Check InfluxDB connection:

```python
from src.database import InfluxDBManager
# Database health is checked on startup and logged
```

## Security Considerations

- **Credentials**: Store InfluxDB tokens in environment variables, not in config files
- **Data Validation**: All incoming data is validated against configured ranges
- **Input Sanitization**: Messages are parsed and sanitized before processing
- **Error Handling**: Comprehensive error handling prevents information leakage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### Version 2.0.0
- Complete modular architecture refactor
- Added comprehensive error handling and retry logic
- Implemented input validation and data sanitization
- Added configuration management with environment variable support
- Implemented structured logging
- Added type hints throughout codebase
- Added comprehensive test suite
- Improved security by removing hardcoded credentials

### Version 1.0.0
- Initial implementation
- Basic LoRa communication
- InfluxDB integration
- File logging