"""
Mock transport for testing.

This module provides a mock transport implementation that allows testing
the PCMI protocol client without actual hardware. Responses can be
pre-configured or dynamically generated using callback functions.

Example:
    >>> from xtconnect.transport import MockTransport
    >>> from xtconnect import ControllerClient
    >>>
    >>> # Create mock with pre-configured responses
    >>> mock = MockTransport()
    >>> mock.add_response(bytes([0x86]))  # SN_ACK
    >>>
    >>> async with ControllerClient(mock) as client:
    ...     await client.connect("00009001")
"""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Callable

from xtconnect.exceptions import TimeoutError, TransportError
from xtconnect.transport.abc import AbstractTransport


class MockTransport(AbstractTransport):
    """
    Mock transport for testing without hardware.

    This transport simulates serial communication by providing pre-configured
    responses. It records all written data for verification in tests.

    Attributes:
        written_data: List of all bytes written to the transport.
        responses: Queue of responses to return on read operations.

    Example:
        >>> mock = MockTransport()
        >>> mock.add_response(b"\\x86")  # SN_ACK
        >>> mock.add_response(b"\\x87")  # BR_ACK
        >>>
        >>> async with mock:
        ...     await mock.write(b"test")
        ...     response = await mock.read_byte()
        ...     assert response == 0x86
        ...     assert mock.written_data == [b"test"]
    """

    def __init__(
        self,
        port_name: str = "mock://test",
        default_timeout: float = 5.0,
    ) -> None:
        """
        Initialize the mock transport.

        Args:
            port_name: Identifier for the mock transport.
            default_timeout: Default timeout for read operations.
        """
        self._port_name = port_name
        self._default_timeout = default_timeout
        self._is_open = False
        self._responses: deque[bytes] = deque()
        self._written_data: list[bytes] = []
        self._read_buffer = bytearray()
        self._response_callback: Callable[[bytes], bytes | None] | None = None

    @property
    def is_open(self) -> bool:
        """Check if the mock transport is open."""
        return self._is_open

    @property
    def port_name(self) -> str:
        """Get the mock port name."""
        return self._port_name

    @property
    def written_data(self) -> list[bytes]:
        """Get all data written to the transport."""
        return self._written_data.copy()

    @property
    def last_written(self) -> bytes | None:
        """Get the most recently written data."""
        return self._written_data[-1] if self._written_data else None

    def add_response(self, response: bytes) -> None:
        """
        Add a response to the queue.

        Responses are returned in FIFO order on read operations.

        Args:
            response: Bytes to return on next read.
        """
        self._responses.append(response)

    def add_responses(self, *responses: bytes) -> None:
        """
        Add multiple responses to the queue.

        Args:
            *responses: Multiple byte responses to add.
        """
        for response in responses:
            self._responses.append(response)

    def set_response_callback(
        self,
        callback: Callable[[bytes], bytes | None] | None,
    ) -> None:
        """
        Set a callback to dynamically generate responses.

        The callback receives the written data and should return the response
        bytes. If it returns None, the next queued response is used instead.

        Args:
            callback: Function that takes written bytes and returns response.
        """
        self._response_callback = callback

    def clear(self) -> None:
        """Clear all written data and pending responses."""
        self._written_data.clear()
        self._responses.clear()
        self._read_buffer.clear()

    def clear_written(self) -> None:
        """Clear only the written data history."""
        self._written_data.clear()

    async def open(self) -> None:
        """Open the mock transport."""
        if self._is_open:
            raise TransportError("Mock transport already open")
        self._is_open = True

    async def close(self) -> None:
        """Close the mock transport."""
        self._is_open = False

    async def write(self, data: bytes) -> None:
        """
        Write data to the mock transport.

        Records the written data and optionally triggers response callback.

        Args:
            data: Bytes to write.

        Raises:
            TransportError: If transport is not open.
        """
        if not self._is_open:
            raise TransportError("Mock transport not open")

        self._written_data.append(bytes(data))

        # Check for callback-generated response
        if self._response_callback:
            response = self._response_callback(data)
            if response is not None:
                self._read_buffer.extend(response)

    async def read_until(
        self,
        terminator: int = 0x0D,
        timeout: float | None = None,
    ) -> bytes:
        """
        Read data until terminator is found.

        Args:
            terminator: Byte to read until.
            timeout: Read timeout (ignored in mock, uses default).

        Returns:
            Bytes including terminator.

        Raises:
            TimeoutError: If no data available and no responses queued.
            TransportError: If transport is not open.
        """
        if not self._is_open:
            raise TransportError("Mock transport not open")

        # Check buffer first
        if terminator in self._read_buffer:
            idx = self._read_buffer.index(terminator)
            result = bytes(self._read_buffer[:idx + 1])
            del self._read_buffer[:idx + 1]
            return result

        # Load next response into buffer
        if self._responses:
            self._read_buffer.extend(self._responses.popleft())

            # Try again with new data
            if terminator in self._read_buffer:
                idx = self._read_buffer.index(terminator)
                result = bytes(self._read_buffer[:idx + 1])
                del self._read_buffer[:idx + 1]
                return result

        raise TimeoutError("No mock response available")

    async def read(self, size: int, timeout: float | None = None) -> bytes:
        """
        Read exact number of bytes.

        Args:
            size: Number of bytes to read.
            timeout: Read timeout (ignored in mock).

        Returns:
            Exactly size bytes.

        Raises:
            TimeoutError: If not enough data available.
            TransportError: If transport is not open.
        """
        if not self._is_open:
            raise TransportError("Mock transport not open")

        # Load responses into buffer until we have enough
        while len(self._read_buffer) < size and self._responses:
            self._read_buffer.extend(self._responses.popleft())

        if len(self._read_buffer) < size:
            raise TimeoutError(f"Not enough mock data: need {size}, have {len(self._read_buffer)}")

        result = bytes(self._read_buffer[:size])
        del self._read_buffer[:size]
        return result

    async def read_byte(self, timeout: float | None = None) -> int:
        """
        Read a single byte.

        Args:
            timeout: Read timeout (ignored in mock).

        Returns:
            Single byte value.

        Raises:
            TimeoutError: If no data available.
            TransportError: If transport is not open.
        """
        if not self._is_open:
            raise TransportError("Mock transport not open")

        # Check buffer
        if self._read_buffer:
            result = self._read_buffer[0]
            del self._read_buffer[0]
            return result

        # Load next response
        if self._responses:
            self._read_buffer.extend(self._responses.popleft())
            if self._read_buffer:
                result = self._read_buffer[0]
                del self._read_buffer[0]
                return result

        raise TimeoutError("No mock response available")

    def discard_buffers(self) -> None:
        """Discard pending data in buffers."""
        self._read_buffer.clear()

    def assert_written(self, expected: bytes, index: int = -1) -> None:
        """
        Assert that specific data was written.

        Args:
            expected: Expected bytes.
            index: Index in written_data list (-1 for last).

        Raises:
            AssertionError: If data doesn't match.
        """
        if not self._written_data:
            raise AssertionError("No data written to mock transport")

        actual = self._written_data[index]
        if actual != expected:
            raise AssertionError(f"Written data mismatch: expected {expected!r}, got {actual!r}")

    def assert_write_count(self, expected: int) -> None:
        """
        Assert number of write operations.

        Args:
            expected: Expected number of writes.

        Raises:
            AssertionError: If count doesn't match.
        """
        actual = len(self._written_data)
        if actual != expected:
            raise AssertionError(f"Write count mismatch: expected {expected}, got {actual}")


class ScriptedMockTransport(MockTransport):
    """
    Mock transport with scripted request/response pairs.

    This variant allows defining expected request/response sequences
    for more structured testing scenarios.

    Example:
        >>> mock = ScriptedMockTransport()
        >>> mock.expect(request=b"\\x20\\x82...", response=b"\\x86")
        >>> mock.expect(request=b"\\x20\\x83...", response=b"\\x87")
    """

    def __init__(self, port_name: str = "mock://scripted") -> None:
        super().__init__(port_name)
        self._script: list[tuple[bytes | None, bytes]] = []
        self._script_index = 0

    def expect(
        self,
        response: bytes,
        request: bytes | None = None,
    ) -> None:
        """
        Add an expected request/response pair.

        Args:
            response: Response to return.
            request: Expected request (None to match any).
        """
        self._script.append((request, response))

    async def write(self, data: bytes) -> None:
        """Write with script validation."""
        if not self._is_open:
            raise TransportError("Mock transport not open")

        self._written_data.append(bytes(data))

        # Check script
        if self._script_index < len(self._script):
            expected_request, response = self._script[self._script_index]

            if expected_request is not None and data != expected_request:
                raise AssertionError(
                    f"Script mismatch at step {self._script_index}: "
                    f"expected {expected_request!r}, got {data!r}"
                )

            self._read_buffer.extend(response)
            self._script_index += 1

    def reset_script(self) -> None:
        """Reset script to beginning."""
        self._script_index = 0
        self._read_buffer.clear()

    def clear_script(self) -> None:
        """Clear all scripted expectations."""
        self._script.clear()
        self._script_index = 0
