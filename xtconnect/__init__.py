"""
xtconnect - Python library for communicating with Valco agricultural controllers.

This library provides async communication with Valco controllers over RS-485 serial,
supporting the PCMI protocol for reading zone parameters, device data, alarms, and history.

Example:
    >>> from xtconnect import ControllerClient
    >>> from xtconnect.transport import AsyncSerialTransport
    >>>
    >>> async def main():
    ...     transport = AsyncSerialTransport("/dev/ttyUSB0")
    ...     async with ControllerClient(transport) as client:
    ...         await client.connect("00009001")
    ...         async for zone in client.download_zone_parameters():
    ...             print(zone.temp_setpoint.fahrenheit)
"""

from xtconnect.client import ClientState, ControllerClient
from xtconnect.exceptions import (
    ChecksumError,
    ConnectionError,
    ControllerError,
    FrameError,
    ParseError,
    ProtocolError,
    TimeoutError,
    TransportError,
    XTConnectError,
)
from xtconnect.models.records import (
    DeviceType,
    Temperature,
    VersionRecord,
    ZoneParameters,
    ZoneVariables,
)
from xtconnect.transport import AbstractTransport, AsyncSerialTransport

__version__ = "0.1.0"
__all__ = [
    # Client
    "ControllerClient",
    "ClientState",
    # Models
    "Temperature",
    "ZoneParameters",
    "ZoneVariables",
    "VersionRecord",
    "DeviceType",
    # Exceptions
    "XTConnectError",
    "ProtocolError",
    "TimeoutError",
    "ConnectionError",
    "ParseError",
    "ChecksumError",
    "ControllerError",
    "FrameError",
    "TransportError",
    # Transport
    "AbstractTransport",
    "AsyncSerialTransport",
    # Version
    "__version__",
]
