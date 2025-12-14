"""
Async serial transport using pyserial-asyncio.

This module provides the primary transport implementation for communicating
with Valco controllers over RS-485 serial connections.

Serial Configuration (per PCMI specification):
- Baud rate: 19200 (default)
- Data bits: 8
- Parity: Mark (for 9-bit addressing on RS-485 bus)
- Stop bits: 1
- Flow control: None

The RS-485 bus uses 9-bit addressing where the 9th bit (implemented via
Mark parity) indicates an address byte vs. data byte. The controller
monitors the bus and responds only when its address is detected.

Example:
    >>> transport = AsyncSerialTransport("/dev/ttyUSB0")
    >>> async with transport:
    ...     await transport.write(frame)
    ...     response = await transport.read_until()
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from xtconnect.exceptions import TimeoutError, TransportError
from xtconnect.protocol.constants import ProtocolConstants
from xtconnect.transport.abc import AbstractTransport

# Import serial constants - these are available even without hardware
try:
    import serial
    import serial_asyncio

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    # Define constants for type checking when serial is not installed
    serial = None  # type: ignore[assignment]
    serial_asyncio = None  # type: ignore[assignment]

if TYPE_CHECKING:
    pass


class AsyncSerialTransport(AbstractTransport):
    """
    Async serial transport using pyserial-asyncio.

    Provides non-blocking serial communication using Python's asyncio
    framework. This is the primary transport for real hardware communication.

    The transport configures the serial port according to the PCMI protocol
    specification:
    - 19200 baud (configurable)
    - 8 data bits
    - Mark parity (critical for RS-485 9-bit addressing)
    - 1 stop bit

    Attributes:
        port_name: Serial port path (e.g., "/dev/ttyUSB0", "COM3").
        is_open: Whether the port is currently open.

    Example:
        >>> transport = AsyncSerialTransport("/dev/ttyUSB0", baudrate=19200)
        >>> await transport.open()
        >>> try:
        ...     await transport.write(b"\\x20\\x85...")
        ...     response = await transport.read_until(0x0D, timeout=5.0)
        ... finally:
        ...     await transport.close()
    """

    def __init__(
        self,
        port: str,
        baudrate: int = ProtocolConstants.DEFAULT_BAUD_RATE,
        default_timeout: float = ProtocolConstants.DEFAULT_RECEIVE_TIMEOUT,
    ) -> None:
        """
        Initialize the async serial transport.

        Args:
            port: Serial port path (e.g., "/dev/ttyUSB0", "COM3").
            baudrate: Baud rate (default: 19200).
            default_timeout: Default read timeout in seconds (default: 5.0).

        Raises:
            ImportError: If pyserial-asyncio is not installed.
        """
        if not SERIAL_AVAILABLE:
            raise ImportError(
                "pyserial-asyncio is required for serial communication. "
                "Install with: pip install pyserial-asyncio"
            )

        self._port = port
        self._baudrate = baudrate
        self._default_timeout = default_timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._serial_instance: serial.Serial | None = None

    @property
    def is_open(self) -> bool:
        """Check if the serial port is currently open."""
        return (
            self._writer is not None
            and not self._writer.is_closing()
            and self._reader is not None
        )

    @property
    def port_name(self) -> str:
        """Get the serial port path."""
        return self._port

    @property
    def baudrate(self) -> int:
        """Get the configured baud rate."""
        return self._baudrate

    async def open(self) -> None:
        """
        Open the serial port connection.

        Configures the port with PCMI-compliant settings:
        - Mark parity for 9-bit RS-485 addressing
        - 8 data bits, 1 stop bit
        - No flow control

        Raises:
            TransportError: If the port cannot be opened.
        """
        if self.is_open:
            return

        try:
            # Open serial connection with PCMI-compliant settings
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._port,
                baudrate=self._baudrate,
                parity=serial.PARITY_MARK,  # Critical for 9-bit RS-485 addressing
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                # No flow control
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            # Get reference to underlying serial port for buffer operations
            transport = self._writer.transport
            if hasattr(transport, "serial"):
                self._serial_instance = transport.serial

        except serial.SerialException as e:
            raise TransportError(f"Failed to open serial port {self._port}: {e}") from e
        except OSError as e:
            raise TransportError(f"OS error opening {self._port}: {e}") from e
        except Exception as e:
            raise TransportError(f"Unexpected error opening {self._port}: {e}") from e

    async def close(self) -> None:
        """
        Close the serial port connection.

        Safely closes the connection and releases resources. Safe to call
        multiple times.
        """
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                # Ignore errors during close
                pass

        self._reader = None
        self._writer = None
        self._serial_instance = None

    async def write(self, data: bytes) -> None:
        """
        Write data to the serial port.

        Args:
            data: Bytes to transmit.

        Raises:
            TransportError: If the port is not open or write fails.
        """
        if not self.is_open:
            raise TransportError("Serial port is not open")

        try:
            self._writer.write(data)
            await self._writer.drain()
        except Exception as e:
            raise TransportError(f"Write failed: {e}") from e

    async def read_until(
        self,
        terminator: int = ProtocolConstants.ETX,
        timeout: float | None = None,
    ) -> bytes:
        """
        Read data until a terminator byte is received.

        Reads from the serial port until the specified byte is encountered.
        The terminator byte is included in the returned data.

        Args:
            terminator: Byte value to read until (default: 0x0D / CR).
            timeout: Read timeout in seconds. None uses default timeout.

        Returns:
            Bytes read including the terminator.

        Raises:
            TimeoutError: If timeout expires before terminator is received.
            TransportError: If the port is not open or read fails.
        """
        if not self.is_open:
            raise TransportError("Serial port is not open")

        effective_timeout = timeout if timeout is not None else self._default_timeout

        try:
            data = await asyncio.wait_for(
                self._reader.readuntil(bytes([terminator])),
                timeout=effective_timeout,
            )
            return data

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Timeout waiting for terminator 0x{terminator:02X}",
                timeout_seconds=effective_timeout,
            ) from None
        except asyncio.IncompleteReadError as e:
            # Connection closed before terminator was found
            if e.partial:
                raise TransportError(
                    f"Connection closed with partial data: {e.partial.hex()}"
                ) from e
            raise TransportError("Connection closed unexpectedly") from e
        except Exception as e:
            raise TransportError(f"Read failed: {e}") from e

    async def read(self, size: int, timeout: float | None = None) -> bytes:
        """
        Read an exact number of bytes from the serial port.

        Args:
            size: Number of bytes to read.
            timeout: Read timeout in seconds. None uses default timeout.

        Returns:
            Exactly `size` bytes.

        Raises:
            TimeoutError: If timeout expires before all bytes are received.
            TransportError: If the port is not open or read fails.
        """
        if not self.is_open:
            raise TransportError("Serial port is not open")

        if size <= 0:
            return b""

        effective_timeout = timeout if timeout is not None else self._default_timeout

        try:
            data = await asyncio.wait_for(
                self._reader.readexactly(size),
                timeout=effective_timeout,
            )
            return data

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Timeout waiting for {size} bytes",
                timeout_seconds=effective_timeout,
            ) from None
        except asyncio.IncompleteReadError as e:
            raise TransportError(
                f"Connection closed: expected {size} bytes, got {len(e.partial)}"
            ) from e
        except Exception as e:
            raise TransportError(f"Read failed: {e}") from e

    async def read_byte(self, timeout: float | None = None) -> int:
        """
        Read a single byte from the serial port.

        Convenience method for reading single-byte responses like
        acknowledgments.

        Args:
            timeout: Read timeout in seconds. None uses default timeout.

        Returns:
            Single byte value (0-255).

        Raises:
            TimeoutError: If timeout expires.
            TransportError: If the port is not open or read fails.
        """
        data = await self.read(1, timeout)
        return data[0]

    def discard_buffers(self) -> None:
        """
        Discard any pending data in input and output buffers.

        Clears both the receive and transmit buffers on the serial port.
        This is useful for resynchronizing after protocol errors.

        Note: This operates on the underlying serial port and may not
        affect data already buffered by the asyncio layer.
        """
        if self._serial_instance is not None:
            try:
                self._serial_instance.reset_input_buffer()
                self._serial_instance.reset_output_buffer()
            except Exception:
                # Ignore errors - port may be closed
                pass

    def __repr__(self) -> str:
        status = "open" if self.is_open else "closed"
        return f"AsyncSerialTransport({self._port!r}, baudrate={self._baudrate}, {status})"
