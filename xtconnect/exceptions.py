"""
Exception hierarchy for xtconnect.

All exceptions inherit from XTConnectError, providing a clean hierarchy
for error handling. The design follows these principles:

1. Protocol errors (frame parsing, checksum) are distinct from connection errors
2. Controller-reported errors carry the original error code for debugging
3. Parse errors include context about what was being parsed
4. All exceptions provide meaningful error messages
"""

from __future__ import annotations

from typing import Final


class XTConnectError(Exception):
    """
    Base exception for all xtconnect errors.

    All library-specific exceptions inherit from this class, allowing
    callers to catch all xtconnect errors with a single except clause.
    """

    pass


class ProtocolError(XTConnectError):
    """
    Protocol-level error.

    Raised when the protocol is violated, such as:
    - Invalid frame format
    - Unexpected command code
    - Malformed data structure
    """

    pass


class ChecksumError(ProtocolError):
    """
    Checksum validation failure.

    Raised when a received frame's checksum doesn't match the calculated value.
    This typically indicates data corruption during transmission.
    """

    def __init__(
        self,
        message: str = "Checksum validation failed",
        *,
        expected: int | None = None,
        received: int | None = None,
    ) -> None:
        super().__init__(message)
        self.expected = expected
        self.received = received

    def __str__(self) -> str:
        base = super().__str__()
        if self.expected is not None and self.received is not None:
            return f"{base} (expected 0x{self.expected:02X}, got 0x{self.received:02X})"
        return base


class TimeoutError(XTConnectError):  # noqa: A001 - intentionally shadows builtin
    """
    Communication timeout.

    Raised when a response is not received within the expected time.
    This may indicate the controller is not responding or is busy.
    """

    def __init__(
        self,
        message: str = "Communication timeout",
        *,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.timeout_seconds = timeout_seconds

    def __str__(self) -> str:
        base = super().__str__()
        if self.timeout_seconds is not None:
            return f"{base} (after {self.timeout_seconds:.1f}s)"
        return base


class ConnectionError(XTConnectError):  # noqa: A001 - intentionally shadows builtin
    """
    Controller connection error.

    Raised when:
    - Cannot establish connection to controller
    - Connection is unexpectedly lost
    - Serial port cannot be opened
    """

    pass


class ParseError(XTConnectError):
    """
    Record parsing error.

    Raised when a record cannot be parsed, typically due to:
    - Unexpected data format
    - Missing required fields
    - Invalid field values
    """

    def __init__(
        self,
        message: str,
        *,
        record_type: str | None = None,
        offset: int | None = None,
        raw_data: str | None = None,
    ) -> None:
        super().__init__(message)
        self.record_type = record_type
        self.offset = offset
        self.raw_data = raw_data

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.record_type:
            parts.append(f"record_type={self.record_type}")
        if self.offset is not None:
            parts.append(f"offset={self.offset}")
        if self.raw_data:
            # Truncate raw data for display
            display_data = self.raw_data[:40] + "..." if len(self.raw_data) > 40 else self.raw_data
            parts.append(f"data={display_data}")
        return " ".join(parts) if len(parts) > 1 else parts[0]


class ControllerError(XTConnectError):
    """
    Error response from controller.

    Raised when the controller responds with an error code. The error_code
    attribute contains the original PCMI error code for debugging.
    """

    def __init__(self, error_code: int, message: str | None = None) -> None:
        self.error_code = error_code
        self.message = message or ERROR_MESSAGES.get(error_code, "Unknown error")
        super().__init__(f"Controller error 0x{error_code:02X}: {self.message}")


class FrameError(ProtocolError):
    """
    Frame parsing error.

    Raised when a frame cannot be parsed, such as:
    - Incomplete frame received
    - Invalid frame structure
    - Buffer too small
    """

    pass


class TransportError(XTConnectError):
    """
    Transport-level error.

    Raised for low-level transport issues:
    - Serial port errors
    - I/O errors
    - Hardware communication failures
    """

    pass


# Error code to message mapping based on CommandCode error values
ERROR_MESSAGES: Final[dict[int, str]] = {
    0xC1: "Generic error",
    0xC2: "Invalid password",
    0xC3: "Invalid serial number",
    0xC4: "String/data error",
    0xC8: "Zone not found",
    0xCA: "Try again (temporary condition)",
    0xCB: "Controller in use (hands off mode)",
    0xCC: "Resend upload record",
    0xCD: "Device not found",
    0xCE: "Zone not found during upload",
    0xD9: "Checksum error",
    0xDA: "Controller starting up",
    0xDB: "Length mismatch error",
}


def raise_for_error_code(error_code: int) -> None:
    """
    Raise ControllerError if the given code is an error code.

    Args:
        error_code: The command/response code to check.

    Raises:
        ControllerError: If the code is in the error range (0xC0-0xDF).
    """
    if 0xC0 <= error_code <= 0xDF:
        raise ControllerError(error_code)
