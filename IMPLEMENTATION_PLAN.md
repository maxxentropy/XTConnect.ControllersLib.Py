# Implementation Plan: xtconnect-py

**Version:** 0.1.0-draft
**Target:** Python 3.11+
**Dependencies:** `pydantic` (v2), `pyserial-asyncio`, `struct` (std lib)

---

## Executive Summary

This plan details the Python port of XTConnect.ControllersLib, a high-performance RS-485 communication library for Valco agricultural controllers. The Python version (`xtconnect-py`) will leverage:

- **Pydantic v2** for data models with validation (replaces .NET value objects and records)
- **pyserial-asyncio** for async serial communication
- **struct** module for binary parsing (replaces .NET BinaryPrimitives)
- **Python 3.11+** features (type hints, dataclasses, match statements)

---

## Directory Structure

```text
xtconnect/
├── __init__.py
├── protocol/
│   ├── __init__.py
│   ├── constants.py        # CommandCode enums, Protocol constants
│   ├── encoding.py         # Hex <-> Bytes, Latin1 command handling
│   ├── checksums.py        # Additive checksum implementation
│   ├── endianness.py       # [CRITICAL] Swap vs NonSwap strategies
│   ├── length_indicators.py # [CRITICAL] RLI and VLI decoders
│   └── frame_reader.py     # Frame parsing
├── models/
│   ├── __init__.py
│   ├── records.py          # Pydantic models (Zone, Device, History)
│   └── validators.py       # Custom Pydantic validators for binary data
├── parsers/
│   ├── __init__.py
│   ├── hex_reader.py       # HexStringReader port
│   ├── zone_parser.py      # Zone parameter/variable parsers
│   ├── device_registry.py  # Device strategy registry
│   └── devices/            # Device-specific strategies
│       ├── __init__.py
│       ├── air_sensor.py
│       ├── fan.py
│       ├── inlet.py
│       ├── heater.py
│       └── ...             # 21 device types total
├── transport/
│   ├── __init__.py
│   ├── abc.py              # AbstractTransport interface
│   └── serial_async.py     # pyserial-asyncio implementation
├── client.py               # Main ControllerClient (State Machine)
└── exceptions.py           # Typed exceptions
```

---

## Phase 1: Foundation Layer (protocol/)

### 1.1 constants.py - Protocol Constants and Command Codes

**Source Reference:** `XTConnect.Controllers/Protocol/Constants/CommandCode.cs` and `ProtocolConstants.cs`

```python
from enum import IntEnum

class CommandCode(IntEnum):
    """PCMI protocol command codes from CommandCode.cs"""
    # Connection Management
    PCMI_ATTENTION = 0x81
    PCMI_AT_ACK = 0x82
    PCMI_SERIAL_NUMBER = 0x85
    PCMI_SN_ACK = 0x86
    PCMI_BREAK = 0x87
    PCMI_BR_ACK = 0x88

    # Data Request Commands
    PCMI_SEND_PARMDATA = 0x8F
    PCMI_PD_STRING_1 = 0x90
    PCMI_PD_STRING_2 = 0xB7
    PCMI_SEND_VARDATA = 0x91
    PCMI_VD_STRING_1 = 0x92
    PCMI_VD_STRING_2 = 0xB9
    PCMI_SEND_ZONE_PARM = 0x95
    PCMI_ZP_STRING_1 = 0x96
    PCMI_ZP_STRING_2 = 0xB8
    PCMI_SEND_ZONE_VAR = 0x97
    PCMI_ZV_STRING_1 = 0x98
    PCMI_ZV_STRING_2 = 0xBA
    PCMI_SEND_HISTORY = 0x93
    PCMI_HA_STRING = 0x94
    PCMI_HA_STRING_NON_SWAP = 0xB5
    PCMI_SEND_ALARM = 0xA4
    PCMI_SA_STRING = 0xA5
    PCMI_SA_STRING_NON_SWAP = 0xB3
    PCMI_SEND_VERSION = 0x9F
    PCMI_SV_STRING = 0xA0
    PCMI_GET_INFO_RECORD = 0xAC

    # Flow Control
    PCMI_OK_SEND_NEXT = 0x99
    PCMI_END_OF_RECORD = 0x9B
    PCMI_OK_CC_NEXT = 0xA3

    # Error Codes
    PCMI_ER_NO_ZONE = 0xC8
    PCMI_ER_TRY_AGAIN = 0xCA
    PCMI_ER_HANDS_OFF = 0xCB
    PCMI_ER_START_UP = 0xDA
    PCMI_ER_SUM_CHECK = 0xD9
    PCMI_ER_LEN_COUNT = 0xDB

class ProtocolConstants:
    """Protocol constants from ProtocolConstants.cs"""
    STX: int = 0x20  # Space
    ETX: int = 0x0D  # Carriage Return
    DEFAULT_RECEIVE_TIMEOUT: int = 5000
    MAX_RETRIES: int = 6
    COM_BUFFER_SIZE: int = 2048
    SERIAL_NUMBER_LENGTH: int = 8
    MAX_ZONES: int = 9
    NAN_TEMP: int = 0x7FFF
    BASE_YEAR_FOR_DATES: int = 1980
```

---

### 1.2 checksums.py - Additive Checksum Implementation

**Source Reference:** `XTConnect.Controllers/Protocol/Encoding/ChecksumCalculator.cs`

```python
def calculate(data: bytes) -> int:
    """
    Calculate 8-bit additive checksum.
    Algorithm: Sum all bytes, keep only lower 8 bits.
    """
    return sum(data) & 0xFF

def validate(frame: bytes, checksum_offset: int) -> bool:
    """Validate checksum in frame (2 ASCII hex chars at offset)."""
    if len(frame) < checksum_offset + 2:
        return False
    data = frame[:checksum_offset]
    expected = calculate(data)
    try:
        received = int(frame[checksum_offset:checksum_offset+2], 16)
        return expected == received
    except ValueError:
        return False

def append_checksum(data: bytes) -> bytes:
    """Append checksum as 2 uppercase hex ASCII chars."""
    cs = calculate(data)
    return data + f"{cs:02X}".encode('ascii')
```

---

### 1.3 encoding.py - Hex and ASCII Encoding

**Source Reference:** `XTConnect.Controllers/Protocol/Encoding/HexEncoder.cs`

```python
def encode_byte(value: int) -> bytes:
    """Encode byte as 2 uppercase hex ASCII chars."""
    return f"{value:02X}".encode('ascii')

def decode_byte(hex_chars: bytes) -> int:
    """Decode 2 hex ASCII chars to byte value."""
    return int(hex_chars[:2], 16)

def encode_uint16(value: int) -> bytes:
    """Encode 16-bit value as 4 hex chars (big-endian)."""
    return f"{value:04X}".encode('ascii')

def decode_uint16(hex_chars: bytes) -> int:
    """Decode 4 hex chars to 16-bit value (big-endian)."""
    return int(hex_chars[:4], 16)

def hex_to_bytes(hex_string: str) -> bytes:
    """Convert hex string to bytes (for payload conversion)."""
    return bytes.fromhex(hex_string)

def bytes_to_hex(data: bytes) -> str:
    """Convert bytes to uppercase hex string."""
    return data.hex().upper()
```

---

### 1.4 endianness.py - CRITICAL Swap/NonSwap Strategies

**Source Reference:**
- `XTConnect.Controllers.Parsing/Strategies/IEndianStrategy.cs`
- `XTConnect.Controllers.Parsing/Strategies/SwapStrategy.cs`
- `XTConnect.Controllers.Parsing/Strategies/NonSwapStrategy.cs`

**Critical Logic:**
- **RecordFormat < 20:** Uses "Swap" (Big Endian) - older VP controllers
- **RecordFormat >= 20:** Uses "NonSwap" (Little Endian) - VPII and XT controllers

```python
from abc import ABC, abstractmethod
import struct
from typing import Protocol

class EndianStrategy(Protocol):
    """Protocol for endianness handling."""

    def read_uint16(self, data: bytes, offset: int) -> int: ...
    def read_int16(self, data: bytes, offset: int) -> int: ...
    def read_uint32(self, data: bytes, offset: int) -> int: ...
    def read_int32(self, data: bytes, offset: int) -> int: ...
    def write_uint16(self, value: int, data: bytearray, offset: int) -> None: ...

class SwapStrategy:
    """
    Big-endian strategy for RecordFormat < 20 (older controllers).
    Uses '>' format in struct module.
    """
    def read_uint16(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('>H', data, offset)[0]

    def read_int16(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('>h', data, offset)[0]

    def read_uint32(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('>I', data, offset)[0]

    def read_int32(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('>i', data, offset)[0]

    def write_uint16(self, value: int, data: bytearray, offset: int) -> None:
        struct.pack_into('>H', data, offset, value)

class NonSwapStrategy:
    """
    Little-endian strategy for RecordFormat >= 20 (newer controllers).
    Uses '<' format in struct module.
    """
    def read_uint16(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('<H', data, offset)[0]

    def read_int16(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('<h', data, offset)[0]

    def read_uint32(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('<I', data, offset)[0]

    def read_int32(self, data: bytes, offset: int) -> int:
        return struct.unpack_from('<i', data, offset)[0]

def get_strategy(record_format: int) -> EndianStrategy:
    """Select endian strategy based on record format version."""
    if record_format < 20:
        return SwapStrategy()
    return NonSwapStrategy()

# Singleton instances to avoid allocation
SWAP_STRATEGY = SwapStrategy()
NON_SWAP_STRATEGY = NonSwapStrategy()
```

---

### 1.5 length_indicators.py - CRITICAL RLI and VLI Decoders

**Source Reference:** `XTConnect.Controllers/Protocol/Encoding/RliEncoder.cs`

**Critical Notes:**
- **RLI (Record Length Indicator):** Used in Serial Wire Frames
  - Unit: WORD count (1 Word = 2 Bytes)
  - Encoding: ASCII Hex
  - **2-byte RLI is always Little Endian** (even if payload is Big Endian!)
- **VLI (Variable Length Indicator):** Used in Database Parsing
  - Command < 0xB0: 1-byte VLI (2 hex chars)
  - Command >= 0xB0: 2-byte VLI (4 hex chars)

```python
def decode_1byte_rli(rli_chars: bytes) -> int:
    """
    Decode 1-byte RLI (2 ASCII hex chars) to byte count.
    Returns: word_count * 2 (byte count)
    """
    word_count = int(rli_chars[:2], 16)
    return word_count * 2

def decode_2byte_rli(rli_chars: bytes) -> int:
    """
    Decode 2-byte RLI (4 ASCII hex chars) to byte count.
    CRITICAL: RLI uses little-endian byte order!
    Example: "B800" -> low byte 0xB8, high byte 0x00 -> 184 words -> 368 bytes
    """
    low_byte = int(rli_chars[0:2], 16)
    high_byte = int(rli_chars[2:4], 16)
    word_count = (high_byte << 8) | low_byte
    return word_count * 2

def encode_1byte_rli(byte_count: int) -> bytes:
    """Encode byte count as 1-byte RLI (2 hex chars)."""
    if byte_count % 2 != 0:
        raise ValueError("Byte count must be even (word-aligned)")
    word_count = byte_count // 2
    return f"{word_count:02X}".encode('ascii')

def encode_2byte_rli(byte_count: int) -> bytes:
    """
    Encode byte count as 2-byte RLI (4 hex chars).
    CRITICAL: Little-endian encoding.
    """
    if byte_count % 2 != 0:
        raise ValueError("Byte count must be even (word-aligned)")
    word_count = byte_count // 2
    low_byte = word_count & 0xFF
    high_byte = (word_count >> 8) & 0xFF
    return f"{low_byte:02X}{high_byte:02X}".encode('ascii')

def is_2byte_rli(command_code: int) -> bool:
    """Determine if command uses 2-byte RLI based on code."""
    return command_code in {0xB7, 0xB8, 0xB9, 0xBA, 0xB3, 0xB4, 0xB5}

def get_vli_size(command_byte: int) -> int:
    """Determines VLI size in characters based on Command Byte."""
    if command_byte >= 0xB0:
        return 4  # 2-byte VLI (4 hex chars)
    return 2      # 1-byte VLI (2 hex chars)
```

---

## Phase 2: Transport & Framing Layer (transport/)

### 2.1 abc.py - Abstract Transport Interface

**Source Reference:** `XTConnect.Controllers.Core/Communication/ISerialPort.cs`

```python
from abc import ABC, abstractmethod
from typing import Optional
import asyncio

class AbstractTransport(ABC):
    """Abstract serial transport interface."""

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    @property
    @abstractmethod
    def port_name(self) -> str: ...

    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def write(self, data: bytes) -> None: ...

    @abstractmethod
    async def read_until(
        self,
        terminator: int = 0x0D,
        timeout: float = 5.0
    ) -> bytes: ...

    @abstractmethod
    async def read(self, size: int, timeout: float = 5.0) -> bytes: ...

    @abstractmethod
    def discard_buffers(self) -> None: ...
```

---

### 2.2 serial_async.py - pyserial-asyncio Implementation

**Source Reference:** `XTConnect.Controllers.Transports.Serial/RealSerialPort.cs`

```python
import asyncio
import serial_asyncio
import serial
from typing import Optional

class AsyncSerialTransport(AbstractTransport):
    """
    Async serial transport using pyserial-asyncio.

    Configuration per PCMI spec:
    - 19200 baud
    - 8 data bits
    - Mark parity (for 9-bit addressing)
    - 1 stop bit
    """

    def __init__(self, port: str, baudrate: int = 19200):
        self._port = port
        self._baudrate = baudrate
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    @property
    def is_open(self) -> bool:
        return self._writer is not None

    @property
    def port_name(self) -> str:
        return self._port

    async def open(self) -> None:
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self._port,
            baudrate=self._baudrate,
            parity=serial.PARITY_MARK,  # Critical for 9-bit addressing
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )

    async def close(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def read_until(self, terminator: int = 0x0D, timeout: float = 5.0) -> bytes:
        """Read until CR (0x0D) delimiter."""
        try:
            data = await asyncio.wait_for(
                self._reader.readuntil(bytes([terminator])),
                timeout=timeout
            )
            return data
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {timeout}s")

    async def read(self, size: int, timeout: float = 5.0) -> bytes:
        try:
            data = await asyncio.wait_for(
                self._reader.read(size),
                timeout=timeout
            )
            return data
        except asyncio.TimeoutError:
            raise TimeoutError(f"Read timeout after {timeout}s")

    async def write(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()

    def discard_buffers(self) -> None:
        # Clear any pending data
        pass
```

---

### 2.3 frame_reader.py - Frame Parsing

**Source Reference:** `XTConnect.Controllers/Protocol/Frames/FrameReader.cs`

```python
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

class FrameParseResult(Enum):
    SUCCESS = auto()
    EMPTY_BUFFER = auto()
    INCOMPLETE_FRAME = auto()
    INVALID_CHECKSUM = auto()
    INVALID_FORMAT = auto()
    BUFFER_TOO_SMALL = auto()

@dataclass
class ParsedFrame:
    command_byte: int
    payload: bytes
    length_prefix: Optional[int]
    complete_frame: bytes

class FrameReader:
    """
    Parses PCMI protocol frames.

    Frame formats:
    - Simple ack: [CMD]
    - RLI response: [CMD][RLI][DATA][CS][CR]
    - VLI response: [CMD][VLI+DATA][CS][CR]
    - CR-delimited: [CMD][DATA][CS][CR]
    """

    ACKNOWLEDGMENT_CODES = {0x86, 0x88, 0x82, 0xA3, 0xA9, 0x9B,
                           0xC0, 0xC8, 0xCA, 0xCB, 0xD9, 0xDA, 0xDB}
    RLI_COMMANDS = {0x90, 0xB7, 0x92, 0xB9, 0x96, 0xB8, 0x98, 0xBA}
    VLI_COMMANDS = {0x94, 0xB5, 0xA5, 0xB3, 0xAB, 0xB4, 0xAD, 0xB2, 0xB6}
    TWO_BYTE_RLI_COMMANDS = {0xB7, 0xB9, 0xB8, 0xBA}

    def try_parse(self, buffer: bytes) -> Tuple[FrameParseResult, Optional[ParsedFrame], int]:
        """
        Attempt to parse a frame from buffer.
        Returns: (result, parsed_frame, bytes_consumed)
        """
        if not buffer:
            return FrameParseResult.EMPTY_BUFFER, None, 0

        first_byte = buffer[0]

        if first_byte in self.ACKNOWLEDGMENT_CODES:
            return self._parse_acknowledgment(buffer)

        if first_byte in self.RLI_COMMANDS:
            return self._parse_rli_response(buffer, first_byte)

        if first_byte in self.VLI_COMMANDS:
            return self._parse_vli_response(buffer, first_byte)

        # CR-delimited (e.g., version record 0xA0)
        return self._parse_cr_delimited(buffer, first_byte)

    def _parse_acknowledgment(self, buffer: bytes) -> Tuple[FrameParseResult, Optional[ParsedFrame], int]:
        """Parse single-byte acknowledgment."""
        return FrameParseResult.SUCCESS, ParsedFrame(
            command_byte=buffer[0],
            payload=b'',
            length_prefix=None,
            complete_frame=buffer[:1]
        ), 1

    def _parse_rli_response(self, buffer: bytes, cmd: int) -> Tuple[FrameParseResult, Optional[ParsedFrame], int]:
        """Parse RLI-prefixed response."""
        # Implementation details based on RLI size
        pass

    def _parse_vli_response(self, buffer: bytes, cmd: int) -> Tuple[FrameParseResult, Optional[ParsedFrame], int]:
        """Parse VLI-prefixed response."""
        pass

    def _parse_cr_delimited(self, buffer: bytes, cmd: int) -> Tuple[FrameParseResult, Optional[ParsedFrame], int]:
        """Parse CR-terminated response."""
        pass
```

---

## Phase 3: Models Layer (models/)

### 3.1 records.py - Pydantic Models

**Source Reference:**
- `XTConnect.Controllers.Parsing/Records/Zone/ZoneParameters.cs`
- `XTConnect.Controllers.Core/ValueObjects/Temperature.cs`
- `XTConnect.Controllers.Parsing/Records/Device/DeviceType.cs`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import IntEnum

class Temperature(BaseModel):
    """
    Temperature value with 0.1-degree precision.
    Stored as raw int16 (tenths of degree Fahrenheit).
    0x7FFF = NaN (sensor error).
    """
    raw_value: int = Field(ge=-32768, le=32767)

    @property
    def is_nan(self) -> bool:
        return self.raw_value == 0x7FFF

    @property
    def fahrenheit(self) -> Optional[float]:
        if self.is_nan:
            return None
        return self.raw_value / 10.0

    @property
    def celsius(self) -> Optional[float]:
        f = self.fahrenheit
        if f is None:
            return None
        return (f - 32.0) * 5.0 / 9.0

    @classmethod
    def nan(cls) -> "Temperature":
        return cls(raw_value=0x7FFF)

    @classmethod
    def from_fahrenheit(cls, value: float) -> "Temperature":
        raw = int(round(value * 10))
        return cls(raw_value=raw)

    model_config = {"frozen": True}

class SerialNumber(BaseModel):
    """8-digit controller serial number."""
    value: str = Field(min_length=8, max_length=8, pattern=r'^\d{8}$')

    @field_validator('value')
    @classmethod
    def validate_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError('Serial number must contain only digits')
        return v

    model_config = {"frozen": True}

class DeviceType(IntEnum):
    """Device type codes from DeviceType.cs"""
    UNKNOWN = 0
    AIR_SENSOR = 1
    HUMIDITY_SENSOR = 2
    INLET = 3
    CURTAIN = 4
    RIDGE_VENT = 5
    HEATER = 6
    COOLPAD = 7
    FAN = 8
    TIMED = 9
    FEED_SENSOR = 10
    WATER_SENSOR = 11
    STATIC_SENSOR = 12
    DIGITAL_SENSOR = 13
    POSITION_SENSOR = 14
    CHIMNEY = 15
    SWITCH = 16
    VARIABLE_HEATER = 25
    VFD_FAN = 26
    V10_LIGHTS = 27
    GAS_SENSOR = 28

class ZoneParameters(BaseModel):
    """Zone parameter record - immutable."""
    record_size_words: int
    zone_number: int = Field(ge=1, le=9)
    record_type: int
    record_format: int

    # Temperature settings
    temp_setpoint: Temperature
    high_temp_alarm_offset: Temperature
    low_temp_alarm_offset: Temperature
    high_temp_inhibit_offset: Temperature
    low_temp_inhibit_offset: Temperature
    fixed_high_temp_alarm: Temperature

    # Control settings
    interlock_bits: int
    zone_bits: int
    temperature_control: int

    # Humidity settings
    humidity_setpoint: int = Field(ge=0, le=100)
    humidity_off_time: int
    humidity_purge_time: int

    # Animal information
    animal_age: int
    projected_age: int
    weight: int
    begin_head_count_word: int
    mortality_count_word: int
    sold_count_word: int

    # Long head counts (format 3+)
    begin_head_count_long: int = 0
    mortality_count_long: int = 0
    sold_count_long: int = 0
    uses_long_head_counts: bool = False

    raw_data: Optional[str] = None

    model_config = {"frozen": True}
```

---

## Phase 4: Parsing Engine (parsers/)

### 4.1 hex_reader.py - HexStringReader Port

**Source Reference:** `XTConnect.Controllers.Parsing/Infrastructure/HexStringReader.cs`

```python
from typing import Protocol
from ..protocol.endianness import EndianStrategy

class HexStringReader:
    """
    High-performance reader for parsing ASCII hex strings.
    Port of .NET HexStringReader ref struct.
    """

    def __init__(self, data: str, endian_strategy: EndianStrategy):
        self._data = data
        self._endian = endian_strategy
        self._position = 0

    @property
    def position(self) -> int:
        return self._position

    @property
    def remaining(self) -> int:
        return len(self._data) - self._position

    def skip(self, char_count: int) -> None:
        self._position += char_count

    def seek(self, position: int) -> None:
        self._position = position

    def read_byte(self) -> int:
        """Read byte (2 hex chars) and advance."""
        value = int(self._data[self._position:self._position+2], 16)
        self._position += 2
        return value

    def read_sbyte(self) -> int:
        """Read signed byte and advance."""
        value = self.read_byte()
        return value if value < 128 else value - 256

    def read_uint16(self) -> int:
        """Read uint16 (4 hex chars) with endian strategy."""
        b0 = int(self._data[self._position:self._position+2], 16)
        b1 = int(self._data[self._position+2:self._position+4], 16)
        self._position += 4
        return self._endian.read_uint16(bytes([b0, b1]), 0)

    def read_int16(self) -> int:
        """Read int16 (4 hex chars) with endian strategy."""
        b0 = int(self._data[self._position:self._position+2], 16)
        b1 = int(self._data[self._position+2:self._position+4], 16)
        self._position += 4
        return self._endian.read_int16(bytes([b0, b1]), 0)

    def read_uint32(self) -> int:
        """Read uint32 (8 hex chars) with endian strategy."""
        b0 = int(self._data[self._position:self._position+2], 16)
        b1 = int(self._data[self._position+2:self._position+4], 16)
        b2 = int(self._data[self._position+4:self._position+6], 16)
        b3 = int(self._data[self._position+6:self._position+8], 16)
        self._position += 8
        return self._endian.read_uint32(bytes([b0, b1, b2, b3]), 0)

    def peek_byte(self, offset: int) -> int:
        """Read byte at offset without advancing."""
        return int(self._data[offset:offset+2], 16)

    def peek_uint16(self, offset: int) -> int:
        """Read uint16 at offset without advancing."""
        b0 = int(self._data[offset:offset+2], 16)
        b1 = int(self._data[offset+2:offset+4], 16)
        return self._endian.read_uint16(bytes([b0, b1]), 0)
```

---

### 4.2 device_registry.py - Device Strategy Registry

**Source Reference:** `XTConnect.Controllers.Parsing/Parsers/Device/DeviceParserRegistry.cs`

```python
from typing import Dict, Optional, Type
from abc import ABC, abstractmethod
from ..models.records import DeviceType

class DeviceParameterStrategy(ABC):
    """Base class for device parameter parsing strategies."""

    @property
    @abstractmethod
    def device_type(self) -> DeviceType: ...

    @abstractmethod
    def parse(self, reader: "HexStringReader", header: "DeviceRecordHeader",
              raw_data: str) -> "IDeviceParameters": ...

class DeviceVariableStrategy(ABC):
    """Base class for device variable parsing strategies."""

    @property
    @abstractmethod
    def device_type(self) -> DeviceType: ...

    @abstractmethod
    def parse(self, reader: "HexStringReader", header: "DeviceRecordHeader",
              raw_data: str) -> "IDeviceVariables": ...

class DeviceParserRegistry:
    """Registry for device-specific parsing strategies."""

    def __init__(self):
        self._parameter_strategies: Dict[DeviceType, DeviceParameterStrategy] = {}
        self._variable_strategies: Dict[DeviceType, DeviceVariableStrategy] = {}

    def register_parameter_strategy(self, strategy: DeviceParameterStrategy) -> None:
        self._parameter_strategies[strategy.device_type] = strategy

    def register_variable_strategy(self, strategy: DeviceVariableStrategy) -> None:
        self._variable_strategies[strategy.device_type] = strategy

    def get_parameter_strategy(self, device_type: DeviceType) -> Optional[DeviceParameterStrategy]:
        return self._parameter_strategies.get(device_type)

    def get_variable_strategy(self, device_type: DeviceType) -> Optional[DeviceVariableStrategy]:
        return self._variable_strategies.get(device_type)

def create_default_registry() -> DeviceParserRegistry:
    """Create registry with all 21 built-in device strategies."""
    registry = DeviceParserRegistry()
    # Register all device strategies here
    return registry

DEFAULT_REGISTRY = create_default_registry()
```

---

## Phase 5: Client Layer (client.py)

**Source Reference:** Protocol spec from `docs/SERIAL_PROTOCOL_SPECIFICATION.md`

```python
import asyncio
from typing import AsyncGenerator, Optional
from enum import Enum, auto

class ClientState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    DOWNLOADING = auto()

class ControllerClient:
    """
    Main client for PCMI controller communication.
    Implements state machine: Send -> Ack -> SendNext -> ... -> EndOfRecord
    """

    def __init__(self, transport: "AbstractTransport"):
        self._transport = transport
        self._state = ClientState.DISCONNECTED
        self._serial_number: Optional[str] = None

    async def connect(self, serial_number: str) -> bool:
        """Connect to controller by serial number."""
        self._state = ClientState.CONNECTING

        cmd = bytes([CommandCode.PCMI_SERIAL_NUMBER])
        length = b"08"
        sn = serial_number.encode('ascii')
        data = cmd + length + sn
        frame = self._build_frame(data)

        await self._transport.write(frame)
        response = await self._transport.read_until(0x0D)

        if response[0] == CommandCode.PCMI_SN_ACK:
            self._state = ClientState.CONNECTED
            self._serial_number = serial_number
            return True

        self._state = ClientState.DISCONNECTED
        return False

    async def download_zone_parameters(self) -> AsyncGenerator["ZoneParameters", None]:
        """
        Download zone parameters using async generator pattern.
        State machine: SEND_ZONE_PARM -> ZP_STRING -> OK_SEND_NEXT -> ... -> END_OF_RECORD
        """
        frame = self._build_zone_request(CommandCode.PCMI_SEND_ZONE_PARM)
        await self._transport.write(frame)

        while True:
            response = await self._transport.read_until(0x0D)
            result, parsed, _ = FrameReader().try_parse(response)

            if result != FrameParseResult.SUCCESS:
                raise ProtocolError(f"Frame parse failed: {result}")

            if parsed.command_byte == CommandCode.PCMI_END_OF_RECORD:
                break

            if parsed.command_byte in (CommandCode.PCMI_ZP_STRING_1,
                                        CommandCode.PCMI_ZP_STRING_2):
                zone_params = ZoneParameterParser().parse(parsed.payload.hex().upper())
                yield zone_params

                await self._transport.write(
                    bytes([ProtocolConstants.STX, CommandCode.PCMI_OK_SEND_NEXT,
                           ProtocolConstants.ETX])
                )

    async def disconnect(self) -> None:
        """Disconnect from controller (PCMI_BREAK)."""
        frame = bytes([ProtocolConstants.STX, CommandCode.PCMI_BREAK,
                       ProtocolConstants.ETX])
        await self._transport.write(frame)
        await self._transport.read_until(0x0D)
        self._state = ClientState.DISCONNECTED

    def _build_frame(self, data: bytes) -> bytes:
        """Build frame with STX, checksum, ETX."""
        cs = checksums.calculate(data)
        return bytes([ProtocolConstants.STX]) + data + f"{cs:02X}".encode() + \
               bytes([ProtocolConstants.ETX])
```

---

## Phase 6: Exceptions (exceptions.py)

```python
class XTConnectError(Exception):
    """Base exception for xtconnect-py."""
    pass

class ProtocolError(XTConnectError):
    """Protocol-level error (invalid frame, checksum failure)."""
    pass

class TimeoutError(XTConnectError):
    """Communication timeout."""
    pass

class ConnectionError(XTConnectError):
    """Controller connection error."""
    pass

class ParseError(XTConnectError):
    """Record parsing error."""
    pass

class ChecksumError(ProtocolError):
    """Checksum validation failure."""
    pass

class ControllerError(XTConnectError):
    """Error response from controller."""

    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        super().__init__(f"Controller error 0x{error_code:02X}: {message}")

ERROR_MESSAGES = {
    0xC1: "Generic error",
    0xC2: "Invalid password",
    0xC3: "Invalid serial number",
    0xC4: "String/data error",
    0xC8: "Zone not found",
    0xCA: "Try again",
    0xCB: "Controller in use (hands off)",
    0xCC: "Resend upload record",
    0xCD: "Device not found",
    0xCE: "Zone not found during upload",
    0xD9: "Checksum error",
    0xDA: "Controller starting up",
    0xDB: "Length mismatch error",
}
```

---

## Test Strategy

### Unit Tests

```python
# tests/test_endianness.py
def test_swap_strategy_uint16():
    """Test big-endian reading (swap)."""
    strategy = SwapStrategy()
    data = bytes([0x12, 0x34])  # Big-endian: 0x1234
    assert strategy.read_uint16(data, 0) == 0x1234

def test_nonswap_strategy_uint16():
    """Test little-endian reading (non-swap)."""
    strategy = NonSwapStrategy()
    data = bytes([0x34, 0x12])  # Little-endian: 0x1234
    assert strategy.read_uint16(data, 0) == 0x1234

# tests/test_length_indicators.py
def test_2byte_rli_little_endian():
    """Critical: RLI is always little-endian."""
    result = decode_2byte_rli(b"B800")
    assert result == 368  # 0x00B8 = 184 words = 368 bytes

# tests/test_checksums.py
def test_additive_checksum():
    """Test 8-bit additive checksum."""
    data = bytes([0x85, 0x30, 0x38, 0x39, 0x39, 0x39, 0x39, 0x39, 0x39, 0x39, 0x39])
    assert calculate(data) == 0xB5
```

### Integration Tests

```python
# tests/test_integration.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_transport():
    transport = AsyncMock(spec=AbstractTransport)
    transport.is_open = True
    return transport

async def test_connect_sequence(mock_transport):
    """Test full connection sequence."""
    mock_transport.read_until.return_value = bytes([0x86, 0x0D])

    client = ControllerClient(mock_transport)
    result = await client.connect("99999999")

    assert result is True
    mock_transport.write.assert_called_once()
```

---

## Implementation Sequence

### Phase 1: Foundation
1. `protocol/constants.py` - All enums and constants
2. `protocol/checksums.py` - Checksum implementation
3. `protocol/encoding.py` - Hex encoding utilities
4. `protocol/endianness.py` - Critical swap/nonswap strategies
5. `protocol/length_indicators.py` - RLI/VLI decoders
6. Unit tests for all above

### Phase 2: Transport & Framing
1. `transport/abc.py` - Abstract interface
2. `transport/serial_async.py` - pyserial-asyncio implementation
3. `protocol/frame_reader.py` - Frame parsing
4. Integration tests with mock transport

### Phase 3: Models & Parsers
1. `models/records.py` - Core Pydantic models
2. `models/validators.py` - Custom validators
3. `parsers/hex_reader.py` - HexStringReader port
4. `parsers/zone_parser.py` - Zone parameter/variable parsers
5. Unit tests with captured protocol data

### Phase 4: Device Strategies & Client
1. `parsers/device_registry.py` - Strategy registry
2. Implement priority device strategies:
   - AirSensor (simplest)
   - Fan (common)
   - Inlet (common)
   - Heater (common)
3. `client.py` - Main client with async generators
4. `exceptions.py` - Error handling
5. End-to-end tests

### Phase 5: Complete Device Coverage
1. Implement remaining 17 device strategies
2. History record parser
3. Alarm record parser
4. Comprehensive test suite

---

## Critical .NET Source Files Reference

| Python Module | .NET Reference Files |
|---------------|---------------------|
| `protocol/constants.py` | `Protocol/Constants/CommandCode.cs`, `ProtocolConstants.cs` |
| `protocol/checksums.py` | `Protocol/Encoding/ChecksumCalculator.cs` |
| `protocol/encoding.py` | `Protocol/Encoding/HexEncoder.cs` |
| `protocol/endianness.py` | `Parsing/Strategies/SwapStrategy.cs`, `NonSwapStrategy.cs` |
| `protocol/length_indicators.py` | `Protocol/Encoding/RliEncoder.cs` |
| `protocol/frame_reader.py` | `Protocol/Frames/FrameReader.cs` |
| `transport/abc.py` | `Core/Communication/ISerialPort.cs` |
| `transport/serial_async.py` | `Transports.Serial/RealSerialPort.cs` |
| `models/records.py` | `Core/ValueObjects/*.cs`, `Parsing/Records/**/*.cs` |
| `parsers/hex_reader.py` | `Parsing/Infrastructure/HexStringReader.cs` |
| `parsers/device_registry.py` | `Parsing/Parsers/Device/DeviceParserRegistry.cs` |
| `parsers/zone_parser.py` | `Parsing/Parsers/Zone/ZoneParameterParser.cs` |
| `client.py` | `docs/SERIAL_PROTOCOL_SPECIFICATION.md` |
