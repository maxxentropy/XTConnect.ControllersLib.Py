"""
Transport layer for PCMI protocol communication.

This package provides transport implementations for communicating with
Valco controllers over various physical interfaces.

Available transports:
- AsyncSerialTransport: Async serial port using pyserial-asyncio
- MockTransport: Mock transport for testing without hardware

Example:
    >>> from xtconnect.transport import AsyncSerialTransport
    >>> async with AsyncSerialTransport("/dev/ttyUSB0") as transport:
    ...     await transport.write(frame_data)
    ...     response = await transport.read_until()

Testing Example:
    >>> from xtconnect.transport import MockTransport
    >>> mock = MockTransport()
    >>> mock.add_response(bytes([0x86]))  # SN_ACK
"""

from xtconnect.transport.abc import AbstractTransport
from xtconnect.transport.mock import MockTransport, ScriptedMockTransport
from xtconnect.transport.serial_async import AsyncSerialTransport

__all__ = [
    "AbstractTransport",
    "AsyncSerialTransport",
    "MockTransport",
    "ScriptedMockTransport",
]
