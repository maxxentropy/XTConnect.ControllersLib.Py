"""
HexStringReader - High-performance reader for parsing ASCII hex strings.

This module provides a reader that parses hex-encoded binary data from
PCMI protocol records. The reader tracks position and supports various
data types with configurable endianness.

The PCMI protocol transmits binary data as ASCII hex strings where each
byte is represented as two hex characters (e.g., 0x8F becomes "8F").

Key features:
- Position tracking with seek/skip operations
- Endianness-aware multi-byte reads (via EndianStrategy)
- Peek operations for lookahead without advancing
- Bounds checking with clear error messages

Example:
    >>> from xtconnect.parsers import HexStringReader
    >>> from xtconnect.protocol.endianness import NON_SWAP_STRATEGY
    >>> reader = HexStringReader("001234FF", NON_SWAP_STRATEGY)
    >>> reader.read_byte()  # Returns 0x00
    0
    >>> reader.read_uint16()  # Returns 0x3412 (little-endian)
    13330
    >>> reader.read_byte()  # Returns 0xFF
    255
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtconnect.exceptions import ParseError

if TYPE_CHECKING:
    from xtconnect.protocol.endianness import EndianStrategy


class HexStringReader:
    """
    Reader for parsing ASCII hex-encoded binary data.

    Provides methods to read various data types from a hex string,
    tracking position and handling endianness appropriately.

    The reader works with uppercase hex strings where each byte is
    represented as 2 characters (e.g., "8F" for 0x8F).

    Attributes:
        position: Current read position in hex characters.
        remaining: Number of hex characters remaining.
        data: The underlying hex string being read.

    Example:
        >>> reader = HexStringReader("12345678", non_swap_strategy)
        >>> reader.read_byte()  # Reads "12" -> 0x12
        18
        >>> reader.position
        2
        >>> reader.remaining
        6
    """

    __slots__ = ("_data", "_endian", "_position", "_length")

    def __init__(
        self,
        data: str,
        endian_strategy: EndianStrategy,
    ) -> None:
        """
        Initialize the hex string reader.

        Args:
            data: Hex-encoded string (uppercase, 2 chars per byte).
            endian_strategy: Strategy for multi-byte value interpretation.

        Raises:
            ValueError: If data length is odd (incomplete byte).
        """
        if len(data) % 2 != 0:
            raise ValueError(f"Hex string length must be even, got {len(data)}")

        self._data = data.upper()  # Normalize to uppercase
        self._endian = endian_strategy
        self._position = 0
        self._length = len(data)

    @property
    def position(self) -> int:
        """Current position in hex characters (0-indexed)."""
        return self._position

    @property
    def byte_position(self) -> int:
        """Current position in bytes (position // 2)."""
        return self._position // 2

    @property
    def remaining(self) -> int:
        """Number of hex characters remaining to read."""
        return self._length - self._position

    @property
    def remaining_bytes(self) -> int:
        """Number of bytes remaining to read."""
        return self.remaining // 2

    @property
    def data(self) -> str:
        """The underlying hex string."""
        return self._data

    @property
    def endian_strategy(self) -> EndianStrategy:
        """The endianness strategy in use."""
        return self._endian

    def is_at_end(self) -> bool:
        """Check if reader has reached the end of data."""
        return self._position >= self._length

    def has_bytes(self, count: int) -> bool:
        """Check if at least `count` bytes are available to read."""
        return self.remaining >= count * 2

    def _check_bounds(self, char_count: int, operation: str) -> None:
        """Verify sufficient data is available for operation."""
        if self._position + char_count > self._length:
            raise ParseError(
                f"Cannot {operation}: need {char_count} chars, "
                f"have {self.remaining} at position {self._position}",
                offset=self._position,
            )

    # ===== Position Control =====

    def skip(self, char_count: int) -> None:
        """
        Skip forward by the specified number of hex characters.

        Args:
            char_count: Number of hex characters to skip.

        Raises:
            ParseError: If skip would exceed data bounds.
        """
        self._check_bounds(char_count, "skip")
        self._position += char_count

    def skip_bytes(self, byte_count: int) -> None:
        """
        Skip forward by the specified number of bytes.

        Args:
            byte_count: Number of bytes to skip (2 hex chars each).

        Raises:
            ParseError: If skip would exceed data bounds.
        """
        self.skip(byte_count * 2)

    def seek(self, char_position: int) -> None:
        """
        Move to an absolute position in the hex string.

        Args:
            char_position: Target position in hex characters.

        Raises:
            ParseError: If position is out of bounds.
        """
        if char_position < 0 or char_position > self._length:
            raise ParseError(
                f"Invalid seek position {char_position}, valid range is 0-{self._length}",
                offset=char_position,
            )
        self._position = char_position

    def seek_byte(self, byte_position: int) -> None:
        """
        Move to an absolute byte position.

        Args:
            byte_position: Target position in bytes.
        """
        self.seek(byte_position * 2)

    def reset(self) -> None:
        """Reset position to beginning of data."""
        self._position = 0

    # ===== Byte Reading =====

    def read_byte(self) -> int:
        """
        Read a single unsigned byte (2 hex chars) and advance position.

        Returns:
            Unsigned byte value (0-255).

        Raises:
            ParseError: If insufficient data available.
        """
        self._check_bounds(2, "read byte")
        hex_chars = self._data[self._position : self._position + 2]
        self._position += 2
        try:
            return int(hex_chars, 16)
        except ValueError as e:
            raise ParseError(
                f"Invalid hex byte '{hex_chars}'",
                offset=self._position - 2,
            ) from e

    def read_sbyte(self) -> int:
        """
        Read a single signed byte and advance position.

        Returns:
            Signed byte value (-128 to 127).

        Raises:
            ParseError: If insufficient data available.
        """
        value = self.read_byte()
        return value if value < 128 else value - 256

    def read_bytes(self, count: int) -> bytes:
        """
        Read multiple bytes and advance position.

        Args:
            count: Number of bytes to read.

        Returns:
            Bytes object containing the read data.

        Raises:
            ParseError: If insufficient data available.
        """
        char_count = count * 2
        self._check_bounds(char_count, f"read {count} bytes")
        hex_chars = self._data[self._position : self._position + char_count]
        self._position += char_count
        try:
            return bytes.fromhex(hex_chars)
        except ValueError as e:
            raise ParseError(
                f"Invalid hex data '{hex_chars}'",
                offset=self._position - char_count,
            ) from e

    # ===== Multi-byte Reading (Endian-aware) =====

    def read_uint16(self) -> int:
        """
        Read an unsigned 16-bit value using the configured endianness.

        Reads 4 hex chars (2 bytes) and interprets them according to
        the endian strategy.

        Returns:
            Unsigned 16-bit value (0-65535).

        Raises:
            ParseError: If insufficient data available.
        """
        data = self.read_bytes(2)
        return self._endian.read_uint16(data, 0)

    def read_int16(self) -> int:
        """
        Read a signed 16-bit value using the configured endianness.

        Returns:
            Signed 16-bit value (-32768 to 32767).

        Raises:
            ParseError: If insufficient data available.
        """
        data = self.read_bytes(2)
        return self._endian.read_int16(data, 0)

    def read_uint32(self) -> int:
        """
        Read an unsigned 32-bit value using the configured endianness.

        Reads 8 hex chars (4 bytes) and interprets them according to
        the endian strategy.

        Returns:
            Unsigned 32-bit value (0-4294967295).

        Raises:
            ParseError: If insufficient data available.
        """
        data = self.read_bytes(4)
        return self._endian.read_uint32(data, 0)

    def read_int32(self) -> int:
        """
        Read a signed 32-bit value using the configured endianness.

        Returns:
            Signed 32-bit value.

        Raises:
            ParseError: If insufficient data available.
        """
        data = self.read_bytes(4)
        return self._endian.read_int32(data, 0)

    # ===== Peek Operations (No Position Advance) =====

    def peek_byte(self, offset: int = 0) -> int:
        """
        Read a byte at the specified offset without advancing position.

        Args:
            offset: Byte offset from current position (default 0).

        Returns:
            Unsigned byte value at offset.

        Raises:
            ParseError: If offset is out of bounds.
        """
        char_offset = self._position + (offset * 2)
        if char_offset < 0 or char_offset + 2 > self._length:
            raise ParseError(
                f"Peek offset {offset} out of bounds",
                offset=char_offset,
            )
        hex_chars = self._data[char_offset : char_offset + 2]
        try:
            return int(hex_chars, 16)
        except ValueError as e:
            raise ParseError(f"Invalid hex byte '{hex_chars}'", offset=char_offset) from e

    def peek_uint16(self, offset: int = 0) -> int:
        """
        Read a uint16 at the specified byte offset without advancing.

        Args:
            offset: Byte offset from current position.

        Returns:
            Unsigned 16-bit value at offset.

        Raises:
            ParseError: If offset is out of bounds.
        """
        char_offset = self._position + (offset * 2)
        if char_offset < 0 or char_offset + 4 > self._length:
            raise ParseError(
                f"Peek offset {offset} out of bounds for uint16",
                offset=char_offset,
            )
        hex_chars = self._data[char_offset : char_offset + 4]
        try:
            data = bytes.fromhex(hex_chars)
            return self._endian.read_uint16(data, 0)
        except ValueError as e:
            raise ParseError(f"Invalid hex data '{hex_chars}'", offset=char_offset) from e

    def peek_int16(self, offset: int = 0) -> int:
        """
        Read an int16 at the specified byte offset without advancing.

        Args:
            offset: Byte offset from current position.

        Returns:
            Signed 16-bit value at offset.
        """
        char_offset = self._position + (offset * 2)
        if char_offset < 0 or char_offset + 4 > self._length:
            raise ParseError(
                f"Peek offset {offset} out of bounds for int16",
                offset=char_offset,
            )
        hex_chars = self._data[char_offset : char_offset + 4]
        try:
            data = bytes.fromhex(hex_chars)
            return self._endian.read_int16(data, 0)
        except ValueError as e:
            raise ParseError(f"Invalid hex data '{hex_chars}'", offset=char_offset) from e

    # ===== Utility Methods =====

    def read_remaining(self) -> bytes:
        """
        Read all remaining data and advance to end.

        Returns:
            All remaining bytes.
        """
        if self.remaining == 0:
            return b""
        return self.read_bytes(self.remaining_bytes)

    def read_remaining_hex(self) -> str:
        """
        Read all remaining hex characters and advance to end.

        Returns:
            Remaining hex string.
        """
        hex_str = self._data[self._position :]
        self._position = self._length
        return hex_str

    def slice(self, byte_count: int) -> str:
        """
        Get a slice of hex data and advance position.

        Args:
            byte_count: Number of bytes to slice.

        Returns:
            Hex string of the sliced data.

        Raises:
            ParseError: If insufficient data available.
        """
        char_count = byte_count * 2
        self._check_bounds(char_count, f"slice {byte_count} bytes")
        hex_str = self._data[self._position : self._position + char_count]
        self._position += char_count
        return hex_str

    def peek_slice(self, byte_count: int, offset: int = 0) -> str:
        """
        Get a slice of hex data without advancing position.

        Args:
            byte_count: Number of bytes to peek.
            offset: Byte offset from current position.

        Returns:
            Hex string of the peeked data.
        """
        char_offset = self._position + (offset * 2)
        char_count = byte_count * 2
        if char_offset < 0 or char_offset + char_count > self._length:
            raise ParseError(
                f"Peek slice out of bounds",
                offset=char_offset,
            )
        return self._data[char_offset : char_offset + char_count]

    def create_subreader(self, byte_count: int) -> "HexStringReader":
        """
        Create a new reader for a portion of the data and advance position.

        Useful for parsing nested structures where you want to limit
        the scope of parsing to a specific region.

        Args:
            byte_count: Number of bytes for the subreader.

        Returns:
            New HexStringReader for the specified region.

        Raises:
            ParseError: If insufficient data available.
        """
        hex_data = self.slice(byte_count)
        return HexStringReader(hex_data, self._endian)

    def __repr__(self) -> str:
        return (
            f"HexStringReader(pos={self._position}, "
            f"remaining={self.remaining}, "
            f"total={self._length})"
        )

    def __len__(self) -> int:
        """Return total length in hex characters."""
        return self._length
