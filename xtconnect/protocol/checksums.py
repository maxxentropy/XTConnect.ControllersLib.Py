"""
8-bit additive checksum calculation and validation.

The PCMI protocol uses a simple additive checksum:
- Sum all bytes in the data portion
- Keep only the lower 8 bits (modulo 256)
- Encode as 2 ASCII hex characters

The checksum is placed at the end of the frame, before the ETX delimiter.
"""

from __future__ import annotations

from typing import Final

# Pre-computed lookup table for hex encoding
_HEX_CHARS: Final[bytes] = b"0123456789ABCDEF"


def calculate_checksum(data: bytes | bytearray | memoryview) -> int:
    """
    Calculate 8-bit additive checksum over the specified data.

    Algorithm: Sum all bytes, keep only lower 8 bits.

    Args:
        data: Data to checksum (excludes STX, checksum bytes, and ETX).

    Returns:
        8-bit checksum value (0-255).

    Example:
        >>> calculate_checksum(b"\\x85\\x30\\x38")
        0xED
    """
    # Using sum() with & 0xFF is efficient in Python
    # The & operation is applied once at the end rather than per-byte
    return sum(data) & 0xFF


def validate_checksum(
    frame: bytes | bytearray | memoryview,
    checksum_offset: int,
) -> bool:
    """
    Validate that the checksum in the frame matches the calculated value.

    Args:
        frame: Complete frame including checksum bytes (2 ASCII hex chars).
        checksum_offset: Offset to the checksum bytes in the frame.

    Returns:
        True if checksum is valid, False otherwise.

    Example:
        >>> frame = b"\\x85\\x30\\x38ED"  # ED is checksum
        >>> validate_checksum(frame, 3)
        True
    """
    if len(frame) < checksum_offset + 2:
        return False

    # Extract data portion (everything before checksum)
    data = frame[:checksum_offset]

    # Calculate expected checksum
    expected = calculate_checksum(data)

    # Decode received checksum (2 ASCII hex characters)
    try:
        checksum_chars = frame[checksum_offset : checksum_offset + 2]
        # Handle both bytes and string-like inputs
        if isinstance(checksum_chars, memoryview):
            checksum_chars = bytes(checksum_chars)
        received = int(checksum_chars, 16)
        return expected == received
    except (ValueError, TypeError):
        # Invalid hex characters in checksum
        return False


def append_checksum(data: bytes | bytearray) -> bytes:
    """
    Calculate checksum and append as 2 uppercase ASCII hex characters.

    Args:
        data: Data to checksum.

    Returns:
        Original data with 2-character hex checksum appended.

    Example:
        >>> append_checksum(b"\\x85\\x30\\x38")
        b'\\x85\\x30\\x38ED'
    """
    checksum = calculate_checksum(data)
    # Use pre-computed lookup for fast hex encoding
    hex_chars = bytes([_HEX_CHARS[checksum >> 4], _HEX_CHARS[checksum & 0x0F]])
    return bytes(data) + hex_chars


def encode_checksum(checksum: int) -> bytes:
    """
    Encode a checksum value as 2 uppercase ASCII hex characters.

    Args:
        checksum: 8-bit checksum value (0-255).

    Returns:
        2-byte ASCII hex representation.

    Raises:
        ValueError: If checksum is not in range 0-255.

    Example:
        >>> encode_checksum(0xED)
        b'ED'
    """
    if not 0 <= checksum <= 255:
        raise ValueError(f"Checksum must be 0-255, got {checksum}")
    return bytes([_HEX_CHARS[checksum >> 4], _HEX_CHARS[checksum & 0x0F]])


def decode_checksum(hex_chars: bytes | str) -> int:
    """
    Decode 2 ASCII hex characters to a checksum value.

    Args:
        hex_chars: 2 ASCII hex characters.

    Returns:
        Decoded checksum value (0-255).

    Raises:
        ValueError: If input is not valid 2-character hex.

    Example:
        >>> decode_checksum(b'ED')
        0xED
    """
    if len(hex_chars) != 2:
        raise ValueError(f"Checksum must be 2 hex characters, got {len(hex_chars)}")

    if isinstance(hex_chars, bytes):
        hex_chars = hex_chars.decode("ascii")

    return int(hex_chars, 16)
