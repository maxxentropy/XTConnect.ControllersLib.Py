"""
Endianness strategies for PCMI protocol record parsing.

The PCMI protocol uses two different byte orders depending on the controller
firmware version (indicated by the RecordFormat field):

- RecordFormat < 20: Big-endian ("Swap" strategy) - older VP controllers
- RecordFormat >= 20: Little-endian ("NonSwap" strategy) - VPII and XT controllers

The naming comes from the original VLink implementation:
- "Swap" means bytes need to be swapped on x86 (which is little-endian)
- "NonSwap" means native little-endian order, no swapping needed

This module provides strategy classes that encapsulate the endianness handling,
allowing record parsers to work transparently with both byte orders.
"""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from typing import Final, Protocol, runtime_checkable


@runtime_checkable
class EndianStrategy(Protocol):
    """
    Protocol defining the interface for endianness strategies.

    Implementations provide methods to read and write multi-byte values
    with the appropriate byte ordering.
    """

    def read_uint16(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """Read unsigned 16-bit value at offset."""
        ...

    def read_int16(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """Read signed 16-bit value at offset."""
        ...

    def read_uint32(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """Read unsigned 32-bit value at offset."""
        ...

    def read_int32(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """Read signed 32-bit value at offset."""
        ...

    def write_uint16(self, value: int, data: bytearray, offset: int) -> None:
        """Write unsigned 16-bit value at offset."""
        ...

    def write_int16(self, value: int, data: bytearray, offset: int) -> None:
        """Write signed 16-bit value at offset."""
        ...

    def write_uint32(self, value: int, data: bytearray, offset: int) -> None:
        """Write unsigned 32-bit value at offset."""
        ...

    def write_int32(self, value: int, data: bytearray, offset: int) -> None:
        """Write signed 32-bit value at offset."""
        ...


class SwapStrategy:
    """
    Big-endian strategy for RecordFormat < 20 (older controllers).

    These records store words in big-endian byte order. On little-endian
    systems (x86/ARM), bytes must be swapped when reading.

    Example:
        Value 0x1234 is stored as [0x12, 0x34] in the record.
        Reading with this strategy returns 0x1234.
    """

    __slots__ = ()

    def read_uint16(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read unsigned 16-bit value in big-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            16-bit unsigned value.
        """
        # Big-endian: high byte first, low byte second
        return (data[offset] << 8) | data[offset + 1]

    def read_int16(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read signed 16-bit value in big-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            16-bit signed value (-32768 to 32767).
        """
        value = self.read_uint16(data, offset)
        # Convert to signed using two's complement
        return value if value < 0x8000 else value - 0x10000

    def read_uint32(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read unsigned 32-bit value in big-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            32-bit unsigned value.
        """
        # Big-endian 32-bit: high word at offset, low word at offset+2
        high_word = self.read_uint16(data, offset)
        low_word = self.read_uint16(data, offset + 2)
        return (high_word << 16) | low_word

    def read_int32(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read signed 32-bit value in big-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            32-bit signed value.
        """
        value = self.read_uint32(data, offset)
        # Convert to signed using two's complement
        return value if value < 0x80000000 else value - 0x100000000

    def write_uint16(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write unsigned 16-bit value in big-endian order.

        Args:
            value: Value to write (0-65535).
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        # Big-endian: high byte first, low byte second
        data[offset] = (value >> 8) & 0xFF
        data[offset + 1] = value & 0xFF

    def write_int16(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write signed 16-bit value in big-endian order.

        Args:
            value: Value to write (-32768 to 32767).
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        self.write_uint16(value & 0xFFFF, data, offset)

    def write_uint32(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write unsigned 32-bit value in big-endian order.

        Args:
            value: Value to write (0-4294967295).
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        # Big-endian 32-bit: high word at offset, low word at offset+2
        self.write_uint16((value >> 16) & 0xFFFF, data, offset)
        self.write_uint16(value & 0xFFFF, data, offset + 2)

    def write_int32(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write signed 32-bit value in big-endian order.

        Args:
            value: Value to write.
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        self.write_uint32(value & 0xFFFFFFFF, data, offset)


class NonSwapStrategy:
    """
    Little-endian strategy for RecordFormat >= 20 (newer controllers).

    These records store values in native little-endian byte order.
    On little-endian systems (x86/ARM), no byte swapping is needed.

    Uses Python's struct module for efficient native-endian operations.

    Example:
        Value 0x1234 is stored as [0x34, 0x12] in the record.
        Reading with this strategy returns 0x1234.
    """

    __slots__ = ()

    def read_uint16(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read unsigned 16-bit value in little-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            16-bit unsigned value.
        """
        return struct.unpack_from("<H", data, offset)[0]

    def read_int16(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read signed 16-bit value in little-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            16-bit signed value (-32768 to 32767).
        """
        return struct.unpack_from("<h", data, offset)[0]

    def read_uint32(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read unsigned 32-bit value in little-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            32-bit unsigned value.
        """
        return struct.unpack_from("<I", data, offset)[0]

    def read_int32(self, data: bytes | bytearray | memoryview, offset: int) -> int:
        """
        Read signed 32-bit value in little-endian order.

        Args:
            data: Source buffer.
            offset: Byte offset to read from.

        Returns:
            32-bit signed value.
        """
        return struct.unpack_from("<i", data, offset)[0]

    def write_uint16(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write unsigned 16-bit value in little-endian order.

        Args:
            value: Value to write (0-65535).
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        struct.pack_into("<H", data, offset, value)

    def write_int16(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write signed 16-bit value in little-endian order.

        Args:
            value: Value to write (-32768 to 32767).
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        struct.pack_into("<h", data, offset, value)

    def write_uint32(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write unsigned 32-bit value in little-endian order.

        Args:
            value: Value to write (0-4294967295).
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        struct.pack_into("<I", data, offset, value)

    def write_int32(self, value: int, data: bytearray, offset: int) -> None:
        """
        Write signed 32-bit value in little-endian order.

        Args:
            value: Value to write.
            data: Destination buffer.
            offset: Byte offset to write to.
        """
        struct.pack_into("<i", data, offset, value)


# Singleton instances to avoid repeated allocations
SWAP_STRATEGY: Final[SwapStrategy] = SwapStrategy()
"""Singleton big-endian strategy instance for RecordFormat < 20."""

NON_SWAP_STRATEGY: Final[NonSwapStrategy] = NonSwapStrategy()
"""Singleton little-endian strategy instance for RecordFormat >= 20."""

# Threshold for determining endianness
RECORD_FORMAT_THRESHOLD: Final[int] = 20
"""RecordFormat values >= this use little-endian (NonSwap)."""


def get_endian_strategy(record_format: int) -> SwapStrategy | NonSwapStrategy:
    """
    Get the appropriate endianness strategy for a record format version.

    Args:
        record_format: The RecordFormat field value from the record header.

    Returns:
        SwapStrategy for RecordFormat < 20 (big-endian),
        NonSwapStrategy for RecordFormat >= 20 (little-endian).

    Example:
        >>> strategy = get_endian_strategy(14)
        >>> isinstance(strategy, SwapStrategy)
        True
        >>> strategy = get_endian_strategy(20)
        >>> isinstance(strategy, NonSwapStrategy)
        True
    """
    if record_format < RECORD_FORMAT_THRESHOLD:
        return SWAP_STRATEGY
    return NON_SWAP_STRATEGY


def is_big_endian_format(record_format: int) -> bool:
    """
    Check if a record format uses big-endian byte order.

    Args:
        record_format: The RecordFormat field value.

    Returns:
        True if big-endian (RecordFormat < 20), False otherwise.
    """
    return record_format < RECORD_FORMAT_THRESHOLD


def is_little_endian_format(record_format: int) -> bool:
    """
    Check if a record format uses little-endian byte order.

    Args:
        record_format: The RecordFormat field value.

    Returns:
        True if little-endian (RecordFormat >= 20), False otherwise.
    """
    return record_format >= RECORD_FORMAT_THRESHOLD
