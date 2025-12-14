"""
Abstract transport interface for PCMI protocol communication.

This module defines the abstract base class for all transport implementations.
Transports handle the low-level communication with controllers over serial
ports or other physical interfaces.

The transport layer is responsible for:
- Opening/closing the physical connection
- Reading and writing raw bytes
- Timeout handling
- Buffer management

Implementations:
- AsyncSerialTransport: pyserial-asyncio based serial port
- (Future) MockTransport: For testing without hardware
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


class AbstractTransport(ABC):
    """
    Abstract base class for PCMI protocol transports.

    Transports provide async read/write operations for communicating with
    Valco controllers. All transport implementations must inherit from this
    class and implement all abstract methods.

    Transports support async context manager protocol for safe resource
    management:

        async with AsyncSerialTransport("/dev/ttyUSB0") as transport:
            await transport.write(frame)
            response = await transport.read_until()

    Attributes:
        is_open: Whether the transport connection is currently open.
        port_name: Identifier for the transport (e.g., serial port name).
    """

    @property
    @abstractmethod
    def is_open(self) -> bool:
        """
        Check if the transport connection is currently open.

        Returns:
            True if connected and ready for I/O, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def port_name(self) -> str:
        """
        Get the transport identifier.

        Returns:
            Port name or identifier string (e.g., "/dev/ttyUSB0", "COM3").
        """
        ...

    @abstractmethod
    async def open(self) -> None:
        """
        Open the transport connection.

        Establishes the physical connection to the controller. For serial
        transports, this opens the serial port with the configured settings.

        Raises:
            TransportError: If the connection cannot be established.
            ConnectionError: If already connected or port is in use.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """
        Close the transport connection.

        Releases the physical connection and any associated resources.
        Safe to call multiple times (idempotent).

        After closing, the transport can be reopened with open().
        """
        ...

    @abstractmethod
    async def write(self, data: bytes) -> None:
        """
        Write data to the transport.

        Sends raw bytes to the controller. The data should be a complete
        protocol frame including any delimiters and checksum.

        Args:
            data: Bytes to send.

        Raises:
            TransportError: If the transport is not open or write fails.
        """
        ...

    @abstractmethod
    async def read_until(
        self,
        terminator: int = 0x0D,
        timeout: float | None = None,
    ) -> bytes:
        """
        Read data until a terminator byte is received.

        Reads from the transport until the specified terminator byte is
        encountered. The terminator is included in the returned data.

        Args:
            terminator: Byte value to read until (default: 0x0D / CR).
            timeout: Read timeout in seconds. None uses transport default.

        Returns:
            Bytes read including the terminator.

        Raises:
            TimeoutError: If timeout expires before terminator is received.
            TransportError: If the transport is not open or read fails.
        """
        ...

    @abstractmethod
    async def read(self, size: int, timeout: float | None = None) -> bytes:
        """
        Read an exact number of bytes from the transport.

        Blocks until exactly `size` bytes have been received or timeout
        expires.

        Args:
            size: Number of bytes to read.
            timeout: Read timeout in seconds. None uses transport default.

        Returns:
            Exactly `size` bytes.

        Raises:
            TimeoutError: If timeout expires before all bytes are received.
            TransportError: If the transport is not open or read fails.
        """
        ...

    @abstractmethod
    async def read_byte(self, timeout: float | None = None) -> int:
        """
        Read a single byte from the transport.

        Convenience method for reading single-byte acknowledgments.

        Args:
            timeout: Read timeout in seconds. None uses transport default.

        Returns:
            Single byte value (0-255).

        Raises:
            TimeoutError: If timeout expires.
            TransportError: If the transport is not open or read fails.
        """
        ...

    @abstractmethod
    def discard_buffers(self) -> None:
        """
        Discard any pending data in input and output buffers.

        Clears both the receive and transmit buffers. Useful for
        resynchronizing after errors.
        """
        ...

    async def __aenter__(self) -> AbstractTransport:
        """Async context manager entry - opens the transport."""
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit - closes the transport."""
        await self.close()
