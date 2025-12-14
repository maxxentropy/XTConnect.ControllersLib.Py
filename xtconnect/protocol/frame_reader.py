"""
PCMI protocol frame parsing.

This module handles parsing of incoming protocol frames from the wire format
into structured data. The PCMI protocol uses several frame formats:

1. **Acknowledgment frames**: Single command byte (no payload, no checksum)
   - Used for: SN_ACK, BR_ACK, END_OF_RECORD, errors
   - Format: [CMD]

2. **RLI frames**: Record Length Indicator prefix
   - Used for: Zone/device parameter and variable data
   - Format: [CMD][RLI][DATA][CS][CR]
   - RLI can be 1-byte (2 hex chars) or 2-byte (4 hex chars)
   - Data length = RLI value * 2 (RLI is in words)

3. **VLI frames**: Variable Length Indicator prefix
   - Used for: History, alarm, and info records
   - Format: [CMD][VLI][DATA][CS][CR]
   - VLI size determined by command byte (< 0xB0 = 1 byte, >= 0xB0 = 2 bytes)

4. **CR-delimited frames**: No length indicator
   - Used for: Version records
   - Format: [CMD][DATA][CS][CR]

Wire Format Notes:
- Command byte is raw (not hex encoded)
- RLI/VLI and DATA are ASCII hex encoded (2 chars per byte)
- Checksum is 2 ASCII hex characters
- CR terminator is 0x0D
- STX (0x20) may precede frames from master but not typically in responses
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from xtconnect.protocol.checksums import calculate_checksum
from xtconnect.protocol.constants import (
    ACKNOWLEDGMENT_CODES,
    ONE_BYTE_RLI_COMMANDS,
    TWO_BYTE_RLI_COMMANDS,
    VLI_COMMANDS,
    CommandCode,
    ProtocolConstants,
)
from xtconnect.protocol.length_indicators import (
    decode_1byte_rli,
    decode_2byte_rli,
    get_vli_size,
)

if TYPE_CHECKING:
    from collections.abc import Buffer


class FrameParseResult(Enum):
    """
    Result codes for frame parsing operations.

    These indicate the outcome of attempting to parse a frame from
    a byte buffer.
    """

    SUCCESS = auto()
    """Frame was successfully parsed and validated."""

    EMPTY_BUFFER = auto()
    """Buffer is empty, no data to parse."""

    INCOMPLETE_FRAME = auto()
    """Buffer contains partial frame data, more bytes needed."""

    INVALID_CHECKSUM = auto()
    """Frame checksum validation failed (data corruption)."""

    INVALID_FORMAT = auto()
    """Frame format is invalid or malformed."""

    UNKNOWN_COMMAND = auto()
    """Command byte is not recognized."""


@dataclass(frozen=True)
class ParsedFrame:
    """
    A successfully parsed protocol frame.

    Contains the command byte, decoded payload, and metadata about
    the frame structure.

    Attributes:
        command_byte: The command/response code (0x00-0xFF).
        payload: Decoded binary payload (empty for acknowledgments).
        payload_hex: Original hex-encoded payload string.
        length_indicator: Decoded length value if present, None otherwise.
        raw_frame: Complete raw frame bytes as received.
        bytes_consumed: Number of bytes consumed from input buffer.
    """

    command_byte: int
    payload: bytes
    payload_hex: str
    length_indicator: int | None
    raw_frame: bytes
    bytes_consumed: int

    @property
    def command(self) -> CommandCode | int:
        """
        Get command as CommandCode enum if recognized, else raw int.
        """
        try:
            return CommandCode(self.command_byte)
        except ValueError:
            return self.command_byte

    @property
    def is_error(self) -> bool:
        """Check if this frame represents an error response."""
        return 0xC0 <= self.command_byte <= 0xDF

    @property
    def is_acknowledgment(self) -> bool:
        """Check if this is a single-byte acknowledgment."""
        return self.command_byte in ACKNOWLEDGMENT_CODES

    @property
    def is_end_of_record(self) -> bool:
        """Check if this signals end of multi-record sequence."""
        return self.command_byte == CommandCode.PCMI_END_OF_RECORD

    def __repr__(self) -> str:
        cmd_name = self.command.name if isinstance(self.command, CommandCode) else f"0x{self.command_byte:02X}"
        if self.payload:
            return f"ParsedFrame({cmd_name}, payload={len(self.payload)} bytes)"
        return f"ParsedFrame({cmd_name})"


@dataclass(frozen=True)
class FrameParseError:
    """
    Details about a frame parsing failure.

    Provides diagnostic information when parsing fails.
    """

    result: FrameParseResult
    message: str
    position: int = 0
    partial_data: bytes = b""


class FrameReader:
    """
    PCMI protocol frame parser.

    Parses incoming byte streams into structured frames. The parser is
    stateless and can be reused for multiple parse operations.

    The parser handles the various frame formats used by the protocol
    and performs checksum validation on applicable frames.

    Example:
        >>> reader = FrameReader()
        >>> # Parse a single-byte acknowledgment
        >>> result, frame = reader.parse(bytes([0x86]))
        >>> assert result == FrameParseResult.SUCCESS
        >>> assert frame.command_byte == 0x86  # SN_ACK

        >>> # Parse an RLI response
        >>> result, frame = reader.parse(rli_frame_bytes)
        >>> if result == FrameParseResult.SUCCESS:
        ...     process_zone_data(frame.payload)
    """

    def parse(
        self,
        buffer: bytes | bytearray | memoryview,
    ) -> tuple[FrameParseResult, ParsedFrame | FrameParseError]:
        """
        Parse a frame from the input buffer.

        Examines the first byte to determine the frame type, then
        delegates to the appropriate parser method.

        Args:
            buffer: Input buffer containing frame data.

        Returns:
            Tuple of (result, frame_or_error):
            - On success: (SUCCESS, ParsedFrame)
            - On failure: (error_code, FrameParseError)
        """
        if not buffer:
            return FrameParseResult.EMPTY_BUFFER, FrameParseError(
                result=FrameParseResult.EMPTY_BUFFER,
                message="Buffer is empty",
            )

        # Handle optional STX prefix (master frames have STX, responses may not)
        start_offset = 0
        if buffer[0] == ProtocolConstants.STX:
            start_offset = 1
            if len(buffer) <= 1:
                return FrameParseResult.INCOMPLETE_FRAME, FrameParseError(
                    result=FrameParseResult.INCOMPLETE_FRAME,
                    message="Buffer contains only STX",
                )

        command_byte = buffer[start_offset]

        # Route to appropriate parser based on command type
        if command_byte in ACKNOWLEDGMENT_CODES:
            return self._parse_acknowledgment(buffer, start_offset)

        if command_byte in ONE_BYTE_RLI_COMMANDS:
            return self._parse_rli_frame(buffer, start_offset, rli_chars=2)

        if command_byte in TWO_BYTE_RLI_COMMANDS:
            return self._parse_rli_frame(buffer, start_offset, rli_chars=4)

        if command_byte in VLI_COMMANDS:
            return self._parse_vli_frame(buffer, start_offset)

        # Default: CR-delimited frame (e.g., version record)
        return self._parse_cr_delimited(buffer, start_offset)

    def _parse_acknowledgment(
        self,
        buffer: bytes | bytearray | memoryview,
        offset: int,
    ) -> tuple[FrameParseResult, ParsedFrame | FrameParseError]:
        """
        Parse a single-byte acknowledgment frame.

        Acknowledgments have no payload, checksum, or terminator - just
        a single command byte.
        """
        command_byte = buffer[offset]
        consumed = offset + 1

        frame = ParsedFrame(
            command_byte=command_byte,
            payload=b"",
            payload_hex="",
            length_indicator=None,
            raw_frame=bytes(buffer[:consumed]),
            bytes_consumed=consumed,
        )
        return FrameParseResult.SUCCESS, frame

    def _parse_rli_frame(
        self,
        buffer: bytes | bytearray | memoryview,
        offset: int,
        rli_chars: int,
    ) -> tuple[FrameParseResult, ParsedFrame | FrameParseError]:
        """
        Parse a frame with Record Length Indicator.

        Frame format: [CMD][RLI][DATA][CS][CR]
        - CMD: 1 byte (raw)
        - RLI: 2 or 4 hex chars (word count)
        - DATA: Variable length hex chars (RLI * 2 * 2 chars)
        - CS: 2 hex chars
        - CR: 1 byte (0x0D)

        Args:
            buffer: Input buffer.
            offset: Start position in buffer.
            rli_chars: Number of RLI characters (2 or 4).
        """
        # Minimum frame: CMD(1) + RLI(2-4) + CS(2) + CR(1)
        min_size = offset + 1 + rli_chars + 2 + 1
        if len(buffer) < min_size:
            return FrameParseResult.INCOMPLETE_FRAME, FrameParseError(
                result=FrameParseResult.INCOMPLETE_FRAME,
                message=f"Buffer too small for RLI frame (need {min_size}, have {len(buffer)})",
                position=offset,
            )

        command_byte = buffer[offset]

        # Extract and decode RLI
        rli_start = offset + 1
        rli_end = rli_start + rli_chars
        rli_bytes = bytes(buffer[rli_start:rli_end])

        try:
            if rli_chars == 2:
                data_byte_count = decode_1byte_rli(rli_bytes)
            else:
                data_byte_count = decode_2byte_rli(rli_bytes)
        except ValueError as e:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message=f"Invalid RLI: {e}",
                position=rli_start,
            )

        # Data is hex-encoded: char count = byte count * 2
        data_char_count = data_byte_count * 2

        # Calculate expected total frame size
        # CMD(1) + RLI(rli_chars) + DATA(data_char_count) + CS(2) + CR(1)
        expected_size = offset + 1 + rli_chars + data_char_count + 2 + 1

        if len(buffer) < expected_size:
            return FrameParseResult.INCOMPLETE_FRAME, FrameParseError(
                result=FrameParseResult.INCOMPLETE_FRAME,
                message=f"Incomplete RLI frame (need {expected_size}, have {len(buffer)})",
                position=offset,
            )

        # Extract data portion
        data_start = rli_end
        data_end = data_start + data_char_count
        data_hex_bytes = buffer[data_start:data_end]

        # Extract checksum position
        cs_start = data_end
        cs_end = cs_start + 2

        # Verify CR terminator
        cr_pos = cs_end
        if buffer[cr_pos] != ProtocolConstants.ETX:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message=f"Missing CR terminator at position {cr_pos}, found 0x{buffer[cr_pos]:02X}",
                position=cr_pos,
            )

        # Validate checksum (covers CMD + RLI + DATA, from offset to cs_start)
        checksummed_portion = buffer[offset:cs_start]
        expected_checksum = calculate_checksum(checksummed_portion)

        try:
            cs_bytes = bytes(buffer[cs_start:cs_end])
            received_checksum = int(cs_bytes.decode("ascii"), 16)
        except (ValueError, UnicodeDecodeError):
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message="Invalid checksum format",
                position=cs_start,
            )

        if expected_checksum != received_checksum:
            return FrameParseResult.INVALID_CHECKSUM, FrameParseError(
                result=FrameParseResult.INVALID_CHECKSUM,
                message=f"Checksum mismatch: expected 0x{expected_checksum:02X}, got 0x{received_checksum:02X}",
                position=cs_start,
            )

        # Decode hex payload to bytes
        try:
            data_hex_str = bytes(data_hex_bytes).decode("ascii")
            payload = bytes.fromhex(data_hex_str)
        except (ValueError, UnicodeDecodeError) as e:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message=f"Invalid hex data: {e}",
                position=data_start,
            )

        consumed = expected_size
        frame = ParsedFrame(
            command_byte=command_byte,
            payload=payload,
            payload_hex=data_hex_str,
            length_indicator=data_byte_count,
            raw_frame=bytes(buffer[:consumed]),
            bytes_consumed=consumed,
        )
        return FrameParseResult.SUCCESS, frame

    def _parse_vli_frame(
        self,
        buffer: bytes | bytearray | memoryview,
        offset: int,
    ) -> tuple[FrameParseResult, ParsedFrame | FrameParseError]:
        """
        Parse a frame with Variable Length Indicator.

        Frame format: [CMD][VLI][DATA][CS][CR]
        VLI size depends on command byte:
        - Command < 0xB0: 1-byte VLI (2 hex chars)
        - Command >= 0xB0: 2-byte VLI (4 hex chars)
        """
        command_byte = buffer[offset]
        vli_chars = get_vli_size(command_byte)

        # Minimum frame: CMD(1) + VLI(2-4) + CS(2) + CR(1)
        min_size = offset + 1 + vli_chars + 2 + 1
        if len(buffer) < min_size:
            return FrameParseResult.INCOMPLETE_FRAME, FrameParseError(
                result=FrameParseResult.INCOMPLETE_FRAME,
                message=f"Buffer too small for VLI frame (need {min_size}, have {len(buffer)})",
                position=offset,
            )

        # Extract and decode VLI
        vli_start = offset + 1
        vli_end = vli_start + vli_chars
        vli_bytes = bytes(buffer[vli_start:vli_end])

        try:
            vli_str = vli_bytes.decode("ascii")
            data_byte_count = int(vli_str, 16)
        except (ValueError, UnicodeDecodeError) as e:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message=f"Invalid VLI: {e}",
                position=vli_start,
            )

        # Data is hex-encoded
        data_char_count = data_byte_count * 2

        # Calculate expected total frame size
        expected_size = offset + 1 + vli_chars + data_char_count + 2 + 1

        if len(buffer) < expected_size:
            return FrameParseResult.INCOMPLETE_FRAME, FrameParseError(
                result=FrameParseResult.INCOMPLETE_FRAME,
                message=f"Incomplete VLI frame (need {expected_size}, have {len(buffer)})",
                position=offset,
            )

        # Extract data portion
        data_start = vli_end
        data_end = data_start + data_char_count
        data_hex_bytes = buffer[data_start:data_end]

        # Extract checksum position
        cs_start = data_end
        cs_end = cs_start + 2

        # Verify CR terminator
        cr_pos = cs_end
        if len(buffer) <= cr_pos or buffer[cr_pos] != ProtocolConstants.ETX:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message="Missing CR terminator",
                position=cr_pos if len(buffer) > cr_pos else len(buffer),
            )

        # Validate checksum
        checksummed_portion = buffer[offset:cs_start]
        expected_checksum = calculate_checksum(checksummed_portion)

        try:
            cs_bytes = bytes(buffer[cs_start:cs_end])
            received_checksum = int(cs_bytes.decode("ascii"), 16)
        except (ValueError, UnicodeDecodeError):
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message="Invalid checksum format",
                position=cs_start,
            )

        if expected_checksum != received_checksum:
            return FrameParseResult.INVALID_CHECKSUM, FrameParseError(
                result=FrameParseResult.INVALID_CHECKSUM,
                message=f"Checksum mismatch: expected 0x{expected_checksum:02X}, got 0x{received_checksum:02X}",
                position=cs_start,
            )

        # Decode hex payload to bytes
        try:
            data_hex_str = bytes(data_hex_bytes).decode("ascii")
            payload = bytes.fromhex(data_hex_str)
        except (ValueError, UnicodeDecodeError) as e:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message=f"Invalid hex data: {e}",
                position=data_start,
            )

        consumed = expected_size
        frame = ParsedFrame(
            command_byte=command_byte,
            payload=payload,
            payload_hex=data_hex_str,
            length_indicator=data_byte_count,
            raw_frame=bytes(buffer[:consumed]),
            bytes_consumed=consumed,
        )
        return FrameParseResult.SUCCESS, frame

    def _parse_cr_delimited(
        self,
        buffer: bytes | bytearray | memoryview,
        offset: int,
    ) -> tuple[FrameParseResult, ParsedFrame | FrameParseError]:
        """
        Parse a CR-delimited frame without length indicator.

        Frame format: [CMD][DATA][CS][CR]
        Used for version records and other simple responses.
        """
        # Find CR terminator
        buffer_bytes = bytes(buffer)
        try:
            cr_pos = buffer_bytes.index(ProtocolConstants.ETX, offset)
        except ValueError:
            return FrameParseResult.INCOMPLETE_FRAME, FrameParseError(
                result=FrameParseResult.INCOMPLETE_FRAME,
                message="CR terminator not found",
                position=len(buffer),
            )

        # Minimum: CMD(1) + CS(2) + CR(1) = 4 bytes from offset
        if cr_pos - offset < 3:
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message="Frame too short for CR-delimited format",
                position=offset,
            )

        command_byte = buffer[offset]

        # Checksum is 2 chars before CR
        cs_start = cr_pos - 2
        cs_end = cr_pos

        # Data is between command and checksum
        data_start = offset + 1
        data_end = cs_start
        data_hex_bytes = buffer[data_start:data_end]

        # Validate checksum
        checksummed_portion = buffer[offset:cs_start]
        expected_checksum = calculate_checksum(checksummed_portion)

        try:
            cs_bytes = bytes(buffer[cs_start:cs_end])
            received_checksum = int(cs_bytes.decode("ascii"), 16)
        except (ValueError, UnicodeDecodeError):
            return FrameParseResult.INVALID_FORMAT, FrameParseError(
                result=FrameParseResult.INVALID_FORMAT,
                message="Invalid checksum format",
                position=cs_start,
            )

        if expected_checksum != received_checksum:
            return FrameParseResult.INVALID_CHECKSUM, FrameParseError(
                result=FrameParseResult.INVALID_CHECKSUM,
                message=f"Checksum mismatch: expected 0x{expected_checksum:02X}, got 0x{received_checksum:02X}",
                position=cs_start,
            )

        # Decode hex payload to bytes
        # For CR-delimited frames, data might be ASCII text (like version string)
        # or hex-encoded binary. Try hex first, fall back to raw.
        data_hex_str = ""
        try:
            data_hex_str = bytes(data_hex_bytes).decode("ascii")
            # Check if it looks like valid hex (all hex chars)
            if data_hex_str and all(c in "0123456789ABCDEFabcdef" for c in data_hex_str):
                payload = bytes.fromhex(data_hex_str)
            else:
                # Not hex - use as raw ASCII
                payload = bytes(data_hex_bytes)
                data_hex_str = payload.hex().upper()
        except (ValueError, UnicodeDecodeError):
            # Use raw bytes
            payload = bytes(data_hex_bytes)
            data_hex_str = payload.hex().upper()

        consumed = cr_pos + 1
        frame = ParsedFrame(
            command_byte=command_byte,
            payload=payload,
            payload_hex=data_hex_str,
            length_indicator=None,
            raw_frame=bytes(buffer[:consumed]),
            bytes_consumed=consumed,
        )
        return FrameParseResult.SUCCESS, frame


# Module-level convenience instance
DEFAULT_FRAME_READER: FrameReader = FrameReader()
"""Default FrameReader instance for convenience."""


def parse_frame(
    buffer: bytes | bytearray | memoryview,
) -> tuple[FrameParseResult, ParsedFrame | FrameParseError]:
    """
    Parse a frame using the default frame reader.

    Convenience function that uses the module-level FrameReader instance.

    Args:
        buffer: Input buffer containing frame data.

    Returns:
        Tuple of (result, frame_or_error).
    """
    return DEFAULT_FRAME_READER.parse(buffer)
