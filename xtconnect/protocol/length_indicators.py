"""
Record Length Indicator (RLI) and Variable Length Indicator (VLI) handling.

The PCMI protocol uses length indicators to specify the size of variable-length
data in protocol frames. There are two types:

RLI (Record Length Indicator):
- Used in serial wire frames for zone/device parameter/variable data
- Unit: WORD count (1 word = 2 bytes)
- Can be 1-byte (2 hex chars) or 2-byte (4 hex chars)
- CRITICAL: 2-byte RLI is always LITTLE-ENDIAN, even when payload is big-endian

VLI (Variable Length Indicator):
- Used in database parsing contexts (legacy web service strings)
- Size determined by command byte:
  - Command < 0xB0: 1-byte VLI (2 hex chars)
  - Command >= 0xB0: 2-byte VLI (4 hex chars)
"""

from __future__ import annotations

from typing import Final

from xtconnect.protocol.constants import TWO_BYTE_RLI_COMMANDS

# Maximum sizes for RLI encoding
MAX_1BYTE_RLI_SIZE: Final[int] = 510
"""Maximum byte count for 1-byte RLI (255 words × 2 bytes)."""

MAX_2BYTE_RLI_SIZE: Final[int] = 131070
"""Maximum byte count for 2-byte RLI (65535 words × 2 bytes)."""

# VLI command byte threshold
VLI_2BYTE_THRESHOLD: Final[int] = 0xB0
"""Commands >= this value use 2-byte VLI."""


def decode_1byte_rli(rli_chars: bytes | str) -> int:
    """
    Decode 1-byte RLI (2 ASCII hex characters) to byte count.

    The RLI value represents WORD count, so the byte count is value × 2.

    Args:
        rli_chars: 2 ASCII hex characters.

    Returns:
        Byte count (RLI value × 2).

    Raises:
        ValueError: If input is not exactly 2 hex characters.

    Example:
        >>> decode_1byte_rli(b"10")  # 0x10 = 16 words
        32
        >>> decode_1byte_rli("FF")   # 0xFF = 255 words
        510
    """
    if len(rli_chars) != 2:
        raise ValueError(f"1-byte RLI must be exactly 2 hex characters, got {len(rli_chars)}")

    if isinstance(rli_chars, bytes):
        rli_chars = rli_chars.decode("ascii")

    try:
        word_count = int(rli_chars, 16)
    except ValueError as e:
        raise ValueError(f"Invalid hex in RLI: '{rli_chars}'") from e

    return word_count * 2  # Convert words to bytes


def decode_2byte_rli(rli_chars: bytes | str) -> int:
    """
    Decode 2-byte RLI (4 ASCII hex characters) to byte count.

    CRITICAL: RLI uses little-endian byte order, regardless of payload endianness!

    The first 2 hex chars represent the LOW byte, the last 2 represent the HIGH byte.
    Example: "B800" → low=0xB8, high=0x00 → 0x00B8 = 184 words → 368 bytes

    Args:
        rli_chars: 4 ASCII hex characters.

    Returns:
        Byte count (RLI value × 2).

    Raises:
        ValueError: If input is not exactly 4 hex characters.

    Example:
        >>> decode_2byte_rli(b"B800")  # Little-endian: 0x00B8 = 184 words
        368
        >>> decode_2byte_rli("0001")   # Little-endian: 0x0100 = 256 words
        512
    """
    if len(rli_chars) != 4:
        raise ValueError(f"2-byte RLI must be exactly 4 hex characters, got {len(rli_chars)}")

    if isinstance(rli_chars, bytes):
        rli_chars = rli_chars.decode("ascii")

    try:
        # CRITICAL: Little-endian byte order
        # First 2 chars = LOW byte, last 2 chars = HIGH byte
        low_byte = int(rli_chars[0:2], 16)
        high_byte = int(rli_chars[2:4], 16)
    except ValueError as e:
        raise ValueError(f"Invalid hex in RLI: '{rli_chars}'") from e

    word_count = (high_byte << 8) | low_byte  # Little-endian
    return word_count * 2  # Convert words to bytes


def encode_1byte_rli(byte_count: int) -> bytes:
    """
    Encode byte count as 1-byte RLI (2 ASCII hex characters).

    Args:
        byte_count: Number of bytes (must be even and ≤ 510).

    Returns:
        2-byte ASCII hex representation.

    Raises:
        ValueError: If byte_count is odd or exceeds maximum.

    Example:
        >>> encode_1byte_rli(32)
        b'10'
        >>> encode_1byte_rli(510)
        b'FF'
    """
    if byte_count % 2 != 0:
        raise ValueError(f"Byte count must be even (word-aligned), got {byte_count}")

    if byte_count > MAX_1BYTE_RLI_SIZE:
        raise ValueError(
            f"Byte count {byte_count} exceeds maximum for 1-byte RLI ({MAX_1BYTE_RLI_SIZE})"
        )

    word_count = byte_count // 2
    return f"{word_count:02X}".encode("ascii")


def encode_2byte_rli(byte_count: int) -> bytes:
    """
    Encode byte count as 2-byte RLI (4 ASCII hex characters).

    CRITICAL: RLI uses little-endian byte order!

    Args:
        byte_count: Number of bytes (must be even).

    Returns:
        4-byte ASCII hex representation (little-endian encoded).

    Raises:
        ValueError: If byte_count is odd or exceeds maximum.

    Example:
        >>> encode_2byte_rli(368)  # 184 words = 0x00B8
        b'B800'
        >>> encode_2byte_rli(512)  # 256 words = 0x0100
        b'0001'
    """
    if byte_count % 2 != 0:
        raise ValueError(f"Byte count must be even (word-aligned), got {byte_count}")

    if byte_count > MAX_2BYTE_RLI_SIZE:
        raise ValueError(
            f"Byte count {byte_count} exceeds maximum for 2-byte RLI ({MAX_2BYTE_RLI_SIZE})"
        )

    word_count = byte_count // 2
    # CRITICAL: Little-endian byte order
    # LOW byte in first 2 chars, HIGH byte in last 2 chars
    low_byte = word_count & 0xFF
    high_byte = (word_count >> 8) & 0xFF
    return f"{low_byte:02X}{high_byte:02X}".encode("ascii")


def try_decode_1byte_rli(rli_chars: bytes | str) -> int | None:
    """
    Try to decode 1-byte RLI without raising exceptions.

    Args:
        rli_chars: 2 ASCII hex characters.

    Returns:
        Byte count, or None if invalid.
    """
    try:
        return decode_1byte_rli(rli_chars)
    except ValueError:
        return None


def try_decode_2byte_rli(rli_chars: bytes | str) -> int | None:
    """
    Try to decode 2-byte RLI without raising exceptions.

    Args:
        rli_chars: 4 ASCII hex characters.

    Returns:
        Byte count, or None if invalid.
    """
    try:
        return decode_2byte_rli(rli_chars)
    except ValueError:
        return None


def is_2byte_rli_command(command_code: int) -> bool:
    """
    Determine if a command uses 2-byte RLI.

    Args:
        command_code: The PCMI command code.

    Returns:
        True if the command uses 2-byte RLI, False for 1-byte RLI.

    Example:
        >>> is_2byte_rli_command(0xB7)  # PCMI_PD_STRING_2
        True
        >>> is_2byte_rli_command(0x90)  # PCMI_PD_STRING_1
        False
    """
    return command_code in TWO_BYTE_RLI_COMMANDS


def get_vli_size(command_byte: int) -> int:
    """
    Determine VLI size in hex characters based on command byte.

    VLI (Variable Length Indicator) size is determined by the command:
    - Commands < 0xB0: 1-byte VLI (2 hex chars)
    - Commands >= 0xB0: 2-byte VLI (4 hex chars)

    Args:
        command_byte: The PCMI command code.

    Returns:
        Number of hex characters for the VLI (2 or 4).

    Example:
        >>> get_vli_size(0x94)  # PCMI_HA_STRING
        2
        >>> get_vli_size(0xB5)  # PCMI_HA_NONSWAP_STRING
        4
    """
    if command_byte >= VLI_2BYTE_THRESHOLD:
        return 4  # 2-byte VLI
    return 2  # 1-byte VLI


def decode_vli(vli_chars: bytes | str, is_2byte: bool) -> int:
    """
    Decode a VLI value to byte count.

    VLI values are typically byte counts (not word counts like RLI).

    Args:
        vli_chars: 2 or 4 ASCII hex characters.
        is_2byte: True for 2-byte VLI, False for 1-byte VLI.

    Returns:
        Decoded byte count.

    Raises:
        ValueError: If input length doesn't match expected size.
    """
    expected_len = 4 if is_2byte else 2

    if len(vli_chars) != expected_len:
        raise ValueError(
            f"{'2-byte' if is_2byte else '1-byte'} VLI must be {expected_len} chars, "
            f"got {len(vli_chars)}"
        )

    if isinstance(vli_chars, bytes):
        vli_chars = vli_chars.decode("ascii")

    try:
        return int(vli_chars, 16)
    except ValueError as e:
        raise ValueError(f"Invalid hex in VLI: '{vli_chars}'") from e
