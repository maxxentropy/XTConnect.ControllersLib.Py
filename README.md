# xtconnect

Python library for communicating with Valco agricultural controllers over the PCMI protocol.

## Features

- **Async-first design**: Built on `asyncio` for efficient I/O operations
- **Complete protocol support**: Zone parameters, zone variables, device data, history, and alarms
- **20 device types**: Full support for sensors, fans, heaters, inlets, and more
- **Type-safe**: Full type hints with `py.typed` marker for IDE support
- **Testable**: Includes `MockTransport` for testing without hardware

## Installation

```bash
pip install xtconnect
```

## Quick Start

```python
import asyncio
from xtconnect import ControllerClient
from xtconnect.transport import AsyncSerialTransport

async def main():
    transport = AsyncSerialTransport("/dev/ttyUSB0")

    async with ControllerClient(transport) as client:
        # Connect to controller
        await client.connect("00009001")

        # Download zone parameters
        async for zone in client.download_zone_parameters():
            print(f"Zone {zone.zone_number}: {zone.temp_setpoint.fahrenheit}°F")

        # Download alarms
        async for alarm_list in client.download_alarms():
            for alarm in alarm_list.active_alarms:
                print(f"Active alarm: {alarm.alarm_type_enum.name}")

asyncio.run(main())
```

## API Overview

### ControllerClient

The main client class for communicating with controllers:

```python
from xtconnect import ControllerClient

client = ControllerClient(
    transport,
    timeout=5.0,      # Operation timeout in seconds
    max_retries=3,    # Retry attempts on timeout
)
```

**Connection methods:**
- `connect(serial_number)` - Connect to a controller
- `disconnect()` - Disconnect from the controller

**Download methods:**
- `download_zone_parameters()` - Zone configuration data
- `download_zone_variables()` - Zone runtime data
- `download_device_parameters()` - Device configuration
- `download_device_variables()` - Device runtime data
- `download_history(zone, group)` - Historical data
- `download_alarms(zone)` - Alarm records
- `download_version()` - Firmware version info

### Transports

```python
from xtconnect.transport import AsyncSerialTransport, MockTransport

# Real serial port
transport = AsyncSerialTransport("/dev/ttyUSB0", baudrate=9600)

# Mock for testing
mock = MockTransport()
mock.add_response(bytes([0x86]))  # Queue SN_ACK
```

### Device Registry

Parse device-specific data using the registry:

```python
from xtconnect.parsers import create_default_registry, DeviceType

registry = create_default_registry()

# Check if strategy exists for device type
if registry.has_parameter_strategy(DeviceType.FAN):
    strategy = registry.get_parameter_strategy(DeviceType.FAN)
```

### Models

Key data models:

```python
from xtconnect.models.records import Temperature, ZoneParameters, DeviceType

# Temperature with unit conversion
temp = Temperature(raw_value=720)
print(temp.fahrenheit)  # 72.0
print(temp.celsius)     # 22.2
```

## Supported Device Types

| Category | Device Types |
|----------|-------------|
| Sensors | AirSensor, HumiditySensor, StaticSensor, DigitalSensor, PositionSensor, FeedSensor, WaterSensor, GasSensor |
| Positional | Inlet, Curtain, RidgeVent, Chimney |
| Climate | Heater, CoolPad, Fan, VariableHeater, VfdFan |
| Other | Timed, Switch, V10Lights |

## Testing

Use `MockTransport` for testing without hardware:

```python
import pytest
from xtconnect import ControllerClient
from xtconnect.transport import MockTransport
from xtconnect.protocol.constants import CommandCode

@pytest.mark.asyncio
async def test_connection():
    mock = MockTransport()
    mock.add_response(bytes([CommandCode.PCMI_SN_ACK]))

    client = ControllerClient(mock)
    await client.connect("00009001")

    assert client.is_connected
    assert mock.written_data  # Verify frames were sent
```

## Logging

Enable debug logging to troubleshoot communication:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("xtconnect").setLevel(logging.DEBUG)
```

## Requirements

- Python 3.10+
- pydantic >= 2.0
- pyserial-asyncio >= 0.6

## License

MIT License
