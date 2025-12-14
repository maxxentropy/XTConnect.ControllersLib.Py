"""
Protocol layer for PCMI communication.

This module contains the low-level protocol handling:
- Command codes and protocol constants
- Checksum calculation and validation
- Hex encoding/decoding utilities
- Endianness strategies (Swap/NonSwap)
- Length indicator (RLI/VLI) decoders
- Frame parsing
"""

from xtconnect.protocol.checksums import append_checksum, calculate_checksum, validate_checksum
from xtconnect.protocol.constants import CommandCode, ProtocolConstants
from xtconnect.protocol.encoding import (
    bytes_to_hex,
    decode_byte,
    decode_uint16,
    encode_byte,
    encode_uint16,
    hex_to_bytes,
)
from xtconnect.protocol.endianness import (
    NON_SWAP_STRATEGY,
    SWAP_STRATEGY,
    EndianStrategy,
    NonSwapStrategy,
    SwapStrategy,
    get_endian_strategy,
)
from xtconnect.protocol.frame_reader import (
    DEFAULT_FRAME_READER,
    FrameParseError,
    FrameParseResult,
    FrameReader,
    ParsedFrame,
    parse_frame,
)
from xtconnect.protocol.length_indicators import (
    decode_1byte_rli,
    decode_2byte_rli,
    encode_1byte_rli,
    encode_2byte_rli,
    get_vli_size,
    is_2byte_rli_command,
)

__all__ = [
    # Constants
    "CommandCode",
    "ProtocolConstants",
    # Checksums
    "calculate_checksum",
    "validate_checksum",
    "append_checksum",
    # Encoding
    "encode_byte",
    "decode_byte",
    "encode_uint16",
    "decode_uint16",
    "hex_to_bytes",
    "bytes_to_hex",
    # Endianness
    "EndianStrategy",
    "SwapStrategy",
    "NonSwapStrategy",
    "SWAP_STRATEGY",
    "NON_SWAP_STRATEGY",
    "get_endian_strategy",
    # Length Indicators
    "decode_1byte_rli",
    "decode_2byte_rli",
    "encode_1byte_rli",
    "encode_2byte_rli",
    "is_2byte_rli_command",
    "get_vli_size",
    # Frame Parsing
    "FrameReader",
    "FrameParseResult",
    "ParsedFrame",
    "FrameParseError",
    "parse_frame",
    "DEFAULT_FRAME_READER",
]
