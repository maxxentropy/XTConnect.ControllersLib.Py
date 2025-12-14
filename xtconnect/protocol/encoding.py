"""
Hex encoding and decoding utilities for PCMI protocol.

The PCMI protocol transmits binary data as ASCII hex strings. Each byte
is represented as two hexadecimal characters (0-9, A-F).

For example:
- Byte 0x8F is transmitted as "8F" (2 ASCII characters)
- Word 0x1234 is transmitted as "1234" (4 ASCII characters)
"""

from __future__ import annotations

from typing import Final

# Pre-computed lookup tables for fast encoding/decoding
_HEX_CHARS: Final[bytes] = b"0123456789ABCDEF"
_HEX_DECODE: Final[dict[int, int]] = {
    ord("0"): 0,
    ord("1"): 1,
    ord("2"): 2,
    ord("3"): 3,
    ord("4"): 4,
    ord("5"): 5,
    ord("6"): 6,
    ord("7"): 7,
    ord("8"): 8,
    ord("9"): 9,
    ord("A"): 10,
    ord("B"): 11,
    ord("C"): 12,
    ord("D"): 13,
    ord("E"): 14,
    ord("F"): 15,
    ord("a"): 10,
    ord("b"): 11,
    ord("c"): 12,
    ord("d"): 13,
    ord("e"): 14,
    ord("f"): 15,
}


def encode_byte(value: int) -> bytes:
    """
    Encode a byte value as 2 uppercase ASCII hex characters.

    Args:
        value: Byte value (0-255).

    Returns:
        2-byte ASCII hex representation.

    Raises:
        ValueError: If value is not in range 0-255.

    Example:
        >>> encode_byte(0x8F)
        b'8F'
    """
    if not 0 <= value <= 255:
        raise ValueError(f"Byte value must be 0-255, got {value}")
    return bytes([_HEX_CHARS[value >> 4], _HEX_CHARS[value & 0x0F]])


def decode_byte(hex_chars: bytes | str) -> int:
    """
    Decode 2 ASCII hex characters to a byte value.

    Args:
        hex_chars: 2 ASCII hex characters (case-insensitive).

    Returns:
        Decoded byte value (0-255).

    Raises:
        ValueError: If input is not valid 2-character hex.

    Example:
        >>> decode_byte(b'8F')
        143
    """
    if len(hex_chars) != 2:
        raise ValueError(f"Expected 2 hex characters, got {len(hex_chars)}")

    try:
        if isinstance(hex_chars, str):
            high = _HEX_DECODE[ord(hex_chars[0])]
            low = _HEX_DECODE[ord(hex_chars[1])]
        else:
            high = _HEX_DECODE[hex_chars[0]]
            low = _HEX_DECODE[hex_chars[1]]
        return (high << 4) | low
    except KeyError as e:
        raise ValueError(f"Invalid hex character: {chr(e.args[0])}") from None


def try_decode_byte(hex_chars: bytes | str) -> int | None:
    """
    Try to decode 2 ASCII hex characters to a byte value.

    Args:
        hex_chars: 2 ASCII hex characters (case-insensitive).

    Returns:
        Decoded byte value (0-255), or None if invalid.

    Example:
        >>> try_decode_byte(b'8F')
        143
        >>> try_decode_byte(b'XX')
        None
    """
    try:
        return decode_byte(hex_chars)
    except ValueError:
        return None


def encode_uint16(value: int) -> bytes:
    """
    Encode a 16-bit unsigned value as 4 uppercase ASCII hex characters.

    Uses big-endian byte order (high byte first).

    Args:
        value: 16-bit value (0-65535).

    Returns:
        4-byte ASCII hex representation.

    Raises:
        ValueError: If value is not in range 0-65535.

    Example:
        >>> encode_uint16(0x1234)
        b'1234'
    """
    if not 0 <= value <= 65535:
        raise ValueError(f"UInt16 value must be 0-65535, got {value}")
    return bytes([
        _HEX_CHARS[(value >> 12) & 0x0F],
        _HEX_CHARS[(value >> 8) & 0x0F],
        _HEX_CHARS[(value >> 4) & 0x0F],
        _HEX_CHARS[value & 0x0F],
    ])


def decode_uint16(hex_chars: bytes | str) -> int:
    """
    Decode 4 ASCII hex characters to a 16-bit unsigned value.

    Uses big-endian byte order (high byte first).

    Args:
        hex_chars: 4 ASCII hex characters (case-insensitive).

    Returns:
        Decoded 16-bit value (0-65535).

    Raises:
        ValueError: If input is not valid 4-character hex.

    Example:
        >>> decode_uint16(b'1234')
        4660
    """
    if len(hex_chars) != 4:
        raise ValueError(f"Expected 4 hex characters, got {len(hex_chars)}")

    if isinstance(hex_chars, str):
        hex_chars = hex_chars.encode("ascii")

    return int(hex_chars, 16)


def hex_to_bytes(hex_string: str | bytes) -> bytes:
    """
    Convert a hex string to bytes.

    Args:
        hex_string: Hexadecimal string (must be even length).

    Returns:
        Decoded bytes.

    Raises:
        ValueError: If string is not valid hex or has odd length.

    Example:
        >>> hex_to_bytes("8F1234")
        b'\\x8f\\x124'
    """
    if isinstance(hex_string, bytes):
        hex_string = hex_string.decode("ascii")

    return bytes.fromhex(hex_string)


def bytes_to_hex(data: bytes | bytearray | memoryview) -> str:
    """
    Convert bytes to an uppercase hex string.

    Args:
        data: Binary data to encode.

    Returns:
        Uppercase hexadecimal string.

    Example:
        >>> bytes_to_hex(b'\\x8f\\x124')
        '8F1234'
    """
    return bytes(data).hex().upper()


def encode_serial_number(serial_number: str) -> bytes:
    """
    Encode an 8-digit serial number as ASCII bytes.

    Args:
        serial_number: 8-digit numeric string.

    Returns:
        8-byte ASCII representation.

    Raises:
        ValueError: If serial number is not exactly 8 digits.

    Example:
        >>> encode_serial_number("00009001")
        b'00009001'
    """
    if len(serial_number) != 8 or not serial_number.isdigit():
        raise ValueError(f"Serial number must be exactly 8 digits, got '{serial_number}'")
    return serial_number.encode("ascii")


def decode_serial_number(data: bytes) -> str:
    """
    Decode an 8-byte ASCII serial number.

    Args:
        data: 8-byte ASCII serial number.

    Returns:
        8-digit serial number string.

    Raises:
        ValueError: If data is not exactly 8 ASCII digit bytes.

    Example:
        >>> decode_serial_number(b'00009001')
        '00009001'
    """
    if len(data) != 8:
        raise ValueError(f"Serial number must be exactly 8 bytes, got {len(data)}")

    serial = data.decode("ascii")
    if not serial.isdigit():
        raise ValueError(f"Serial number must contain only digits, got '{serial}'")

    return serial
