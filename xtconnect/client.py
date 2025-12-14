"""
PCMI Controller Client.

This module provides the main client interface for communicating with
Valco agricultural controllers over the PCMI protocol.

The client implements a state machine for the download sequence:
    DISCONNECTED -> connect() -> CONNECTED
    CONNECTED -> download_*() -> DOWNLOADING -> ... -> CONNECTED
    CONNECTED -> disconnect() -> DISCONNECTED

Example:
    >>> from xtconnect import ControllerClient
    >>> from xtconnect.transport import AsyncSerialTransport
    >>>
    >>> async def main():
    ...     transport = AsyncSerialTransport("/dev/ttyUSB0")
    ...     client = ControllerClient(transport)
    ...
    ...     await client.connect("00009001")
    ...     async for zone in client.download_zone_parameters():
    ...         print(f"Zone {zone.zone_number}: {zone.temp_setpoint}")
    ...     await client.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, TypeVar

from xtconnect.exceptions import (
    ConnectionError,
    ControllerError,
    ProtocolError,
    TimeoutError,
)
from xtconnect.models.records import SerialNumber, VersionRecord, ZoneParameters, ZoneVariables
from xtconnect.parsers.zone_parser import parse_zone_parameters, parse_zone_variables
from xtconnect.protocol.checksums import append_checksum
from xtconnect.protocol.constants import (
    ACKNOWLEDGMENT_CODES,
    ERROR_CODES,
    CommandCode,
    ProtocolConstants,
)
from xtconnect.protocol.frame_reader import FrameParseResult, FrameReader, ParsedFrame

if TYPE_CHECKING:
    from xtconnect.parsers.alarm_parser import AlarmList
    from xtconnect.parsers.history_parser import HistoryRecord
    from xtconnect.transport.abc import AbstractTransport

# Module logger
logger = logging.getLogger(__name__)

T = TypeVar("T")


class ClientState(Enum):
    """Controller client connection states."""

    DISCONNECTED = auto()
    """Not connected to any controller."""

    CONNECTING = auto()
    """Attempting to connect to a controller."""

    CONNECTED = auto()
    """Connected and ready for operations."""

    DOWNLOADING = auto()
    """Downloading data from controller."""

    DISCONNECTING = auto()
    """Disconnecting from controller."""


class ControllerClient:
    """
    Client for communicating with Valco PCMI controllers.

    This client manages the connection lifecycle and provides high-level
    methods for downloading zone and device data from controllers.

    The client is designed for async operation and uses async generators
    for streaming multi-record downloads.

    Attributes:
        state: Current connection state.
        serial_number: Connected controller's serial number (if connected).
        transport: The underlying transport layer.

    Example:
        >>> transport = AsyncSerialTransport("/dev/ttyUSB0")
        >>> client = ControllerClient(transport)
        >>>
        >>> # Connect to controller
        >>> await client.connect("00009001")
        >>>
        >>> # Download zone parameters
        >>> async for zone in client.download_zone_parameters():
        ...     print(f"Zone {zone.zone_number} setpoint: {zone.temp_setpoint}")
        >>>
        >>> # Disconnect
        >>> await client.disconnect()
    """

    def __init__(
        self,
        transport: AbstractTransport,
        timeout: float = ProtocolConstants.DEFAULT_RECEIVE_TIMEOUT,
        max_retries: int = ProtocolConstants.MAX_RETRIES,
    ) -> None:
        """
        Initialize the controller client.

        Args:
            transport: Transport layer for communication.
            timeout: Default timeout for operations in seconds.
            max_retries: Maximum retry attempts for failed operations.
        """
        self._transport = transport
        self._timeout = timeout
        self._max_retries = max_retries
        self._state = ClientState.DISCONNECTED
        self._serial_number: str | None = None
        self._frame_reader = FrameReader()

    @property
    def state(self) -> ClientState:
        """Get the current connection state."""
        return self._state

    @property
    def serial_number(self) -> str | None:
        """Get the connected controller's serial number."""
        return self._serial_number

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to a controller."""
        return self._state == ClientState.CONNECTED

    @property
    def transport(self) -> AbstractTransport:
        """Get the underlying transport."""
        return self._transport

    async def connect(self, serial_number: str) -> bool:
        """
        Connect to a controller by serial number.

        Sends the PCMI_SERIAL_NUMBER command and waits for acknowledgment.
        The transport must be opened before calling this method. Retries
        up to max_retries times on timeout.

        Args:
            serial_number: 8-digit controller serial number.

        Returns:
            True if connection successful, False otherwise.

        Raises:
            ConnectionError: If transport is not open or already connected.
            ControllerError: If controller responds with an error.
            TimeoutError: If no response within timeout period after all retries.
        """
        if self._state != ClientState.DISCONNECTED:
            raise ConnectionError(
                f"Cannot connect: client is in {self._state.name} state"
            )

        if not self._transport.is_open:
            logger.debug("Opening transport for connection")
            await self._transport.open()

        # Validate serial number
        sn = SerialNumber(value=serial_number)

        self._state = ClientState.CONNECTING
        logger.info("Connecting to controller %s", serial_number)

        last_exception: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                if attempt > 0:
                    logger.debug("Connection attempt %d/%d", attempt + 1, self._max_retries + 1)
                    self._transport.discard_buffers()

                # Build connection frame: PCMI_SERIAL_NUMBER + length + serial_number
                frame = self._build_frame(
                    CommandCode.PCMI_SERIAL_NUMBER,
                    f"{len(serial_number):02X}".encode("ascii") + serial_number.encode("ascii"),
                )

                await self._transport.write(frame)
                logger.debug("Sent connection frame, waiting for response")

                # Wait for response
                response = await self._read_response()

                if response == CommandCode.PCMI_SN_ACK:
                    self._state = ClientState.CONNECTED
                    self._serial_number = serial_number
                    logger.info("Connected to controller %s", serial_number)
                    return True

                if response in ERROR_CODES:
                    logger.error("Controller error: 0x%02X", response)
                    raise ControllerError(response)

                raise ProtocolError(f"Unexpected response: 0x{response:02X}")

            except TimeoutError as e:
                last_exception = e
                logger.warning("Connection timeout (attempt %d/%d)", attempt + 1, self._max_retries + 1)
                if attempt < self._max_retries:
                    await asyncio.sleep(0.1)  # Brief delay before retry
                continue

            except Exception:
                self._state = ClientState.DISCONNECTED
                raise

        self._state = ClientState.DISCONNECTED
        logger.error("Connection failed after %d attempts", self._max_retries + 1)
        raise last_exception or TimeoutError("Connection timed out")

    async def disconnect(self) -> None:
        """
        Disconnect from the controller.

        Sends the PCMI_BREAK command and waits for acknowledgment.
        Safe to call even if not connected.
        """
        if self._state == ClientState.DISCONNECTED:
            return

        logger.info("Disconnecting from controller %s", self._serial_number)
        self._state = ClientState.DISCONNECTING

        try:
            # Build break frame
            frame = self._build_simple_frame(CommandCode.PCMI_BREAK)
            await self._transport.write(frame)

            # Wait for acknowledgment (best effort)
            try:
                await self._read_response(timeout=1.0)
            except TimeoutError:
                logger.debug("Disconnect acknowledgment timed out (expected)")

        finally:
            self._state = ClientState.DISCONNECTED
            self._serial_number = None
            logger.debug("Disconnected")

    async def download_zone_parameters(self) -> AsyncGenerator[ZoneParameters, None]:
        """
        Download zone parameters from all zones.

        Yields zone parameter records as they are received from the controller.
        Uses the PCMI_SEND_ZONE_PARM command sequence.

        Yields:
            ZoneParameters for each zone in the controller.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.
            ControllerError: If controller responds with error.

        Example:
            >>> async for zone in client.download_zone_parameters():
            ...     print(f"Zone {zone.zone_number}: {zone.temp_setpoint.fahrenheit}F")
        """
        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading zone parameters")

        zone_count = 0
        try:
            # Request zone parameters
            frame = self._build_simple_frame(CommandCode.PCMI_SEND_ZONE_PARM)
            await self._transport.write(frame)

            async for parsed_frame in self._download_records():
                if parsed_frame.command_byte in (
                    CommandCode.PCMI_ZP_STRING_1,
                    CommandCode.PCMI_ZP_STRING_2,
                ):
                    zone_params = parse_zone_parameters(parsed_frame.payload_hex)
                    zone_count += 1
                    yield zone_params

        finally:
            self._state = ClientState.CONNECTED
            logger.debug("Downloaded %d zone parameters", zone_count)

    async def download_zone_variables(self) -> AsyncGenerator[ZoneVariables, None]:
        """
        Download zone variables (runtime data) from all zones.

        Yields zone variable records as they are received from the controller.
        Uses the PCMI_SEND_ZONE_VAR command sequence.

        Yields:
            ZoneVariables for each zone in the controller.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.
        """
        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading zone variables")

        zone_count = 0
        try:
            frame = self._build_simple_frame(CommandCode.PCMI_SEND_ZONE_VAR)
            await self._transport.write(frame)

            async for parsed_frame in self._download_records():
                if parsed_frame.command_byte in (
                    CommandCode.PCMI_ZV_STRING_1,
                    CommandCode.PCMI_ZV_STRING_2,
                ):
                    zone_vars = parse_zone_variables(parsed_frame.payload_hex)
                    zone_count += 1
                    yield zone_vars

        finally:
            self._state = ClientState.CONNECTED
            logger.debug("Downloaded %d zone variables", zone_count)

    async def download_version(self) -> VersionRecord:
        """
        Download version information from the controller.

        Returns:
            VersionRecord containing firmware version and date.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.
        """
        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading version info")

        try:
            frame = self._build_simple_frame(CommandCode.PCMI_SEND_VERSION)
            await self._transport.write(frame)

            response = await self._transport.read_until(
                ProtocolConstants.ETX,
                self._timeout,
            )

            result, parsed = self._frame_reader.parse(response)
            if result != FrameParseResult.SUCCESS:
                raise ProtocolError(f"Failed to parse version response: {result.name}")

            if parsed.command_byte == CommandCode.PCMI_SV_STRING:
                # Version string is ASCII, not hex-encoded
                version_data = parsed.payload.decode("ascii", errors="replace")
                # Format: "VVVVVVVVVVVVVVDDDDDDDD" (14 char version + 8 char date)
                version_string = version_data[:14].strip()
                date_code = version_data[14:22].strip() if len(version_data) >= 22 else ""

                version_record = VersionRecord(
                    version_string=version_string,
                    date_code=date_code,
                    raw_data=parsed.payload_hex,
                )
                logger.debug("Downloaded version: %s", version_string)
                return version_record

            raise ProtocolError(f"Unexpected response: 0x{parsed.command_byte:02X}")

        finally:
            self._state = ClientState.CONNECTED

    async def download_history(
        self,
        zone_number: int = 0,
        group: int = 1,
    ) -> AsyncGenerator[HistoryRecord, None]:
        """
        Download history records from the controller.

        History records contain timestamped environmental data logged at
        regular intervals. Each group represents a different data point
        (temperature, humidity, etc.).

        Args:
            zone_number: Zone to download history for (0 = all zones).
            group: History group to download (1-9).

        Yields:
            HistoryRecord for each history group/zone combination.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.

        Example:
            >>> async for history in client.download_history(zone_number=1, group=1):
            ...     print(f"Zone {history.zone_number}: {len(history.samples)} samples")
        """
        from xtconnect.parsers.history_parser import HistoryRecordParser
        from xtconnect.protocol.endianness import NON_SWAP_STRATEGY, SWAP_STRATEGY

        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading history for zone=%d group=%d", zone_number, group)

        record_count = 0
        try:
            # Build history request: command + zone + group
            request_data = bytes([zone_number, group])
            frame = self._build_frame(CommandCode.PCMI_SEND_HISTORY, request_data)
            await self._transport.write(frame)

            parser = HistoryRecordParser()

            async for parsed_frame in self._download_records():
                if parsed_frame.command_byte in (
                    CommandCode.PCMI_HA_STRING,
                    CommandCode.PCMI_HA_NONSWAP_STRING,
                ):
                    # Determine endianness from command
                    if parsed_frame.command_byte == CommandCode.PCMI_HA_NONSWAP_STRING:
                        strategy = NON_SWAP_STRATEGY
                    else:
                        strategy = SWAP_STRATEGY

                    history = parser.parse(parsed_frame.payload_hex, strategy)
                    record_count += 1
                    yield history

        finally:
            self._state = ClientState.CONNECTED
            logger.debug("Downloaded %d history records", record_count)

    async def download_alarms(self, zone_number: int = 0) -> AsyncGenerator[AlarmList, None]:
        """
        Download alarm records from the controller.

        Alarm records contain information about active and historical
        alarms including type, timestamp, and values.

        Args:
            zone_number: Zone to download alarms for (0 = all zones).

        Yields:
            AlarmList containing alarm records for each zone.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.

        Example:
            >>> async for alarm_list in client.download_alarms():
            ...     for alarm in alarm_list.active_alarms:
            ...         print(f"Active alarm: {alarm.alarm_type_enum.name}")
        """
        from xtconnect.parsers.alarm_parser import AlarmRecordParser
        from xtconnect.protocol.endianness import NON_SWAP_STRATEGY, SWAP_STRATEGY

        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading alarms for zone=%d", zone_number)

        list_count = 0
        try:
            # Build alarm request: command + zone
            request_data = bytes([zone_number])
            frame = self._build_frame(CommandCode.PCMI_SEND_ALARM, request_data)
            await self._transport.write(frame)

            parser = AlarmRecordParser()

            async for parsed_frame in self._download_records():
                if parsed_frame.command_byte in (
                    CommandCode.PCMI_SA_STRING,
                    CommandCode.PCMI_SA_NONSWAP_STRING,
                ):
                    # Determine endianness from command
                    if parsed_frame.command_byte == CommandCode.PCMI_SA_NONSWAP_STRING:
                        strategy = NON_SWAP_STRATEGY
                    else:
                        strategy = SWAP_STRATEGY

                    alarm_list = parser.parse(parsed_frame.payload_hex, strategy)
                    list_count += 1
                    yield alarm_list

        finally:
            self._state = ClientState.CONNECTED
            logger.debug("Downloaded %d alarm lists", list_count)

    async def download_device_parameters(
        self,
        zone_number: int = 0,
    ) -> AsyncGenerator[Any, None]:
        """
        Download device parameters from the controller.

        Device parameters contain configuration for fans, heaters, inlets,
        sensors, and other devices attached to zones.

        Args:
            zone_number: Zone to download device parameters for (0 = all zones).

        Yields:
            Device parameter objects (type varies by device type).
            Use the device registry to get typed device-specific parameters.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.

        Example:
            >>> async for device in client.download_device_parameters():
            ...     print(f"Device: {device.header.device_type.name}")
        """
        from xtconnect.parsers.device_registry import (
            GenericDeviceParameters,
            create_default_registry,
            parse_device_record_header,
        )
        from xtconnect.parsers.hex_reader import HexStringReader
        from xtconnect.protocol.endianness import NON_SWAP_STRATEGY, SWAP_STRATEGY

        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading device parameters for zone=%d", zone_number)

        registry = create_default_registry()
        device_count = 0

        try:
            # Build request: command + zone
            request_data = bytes([zone_number])
            frame = self._build_frame(CommandCode.PCMI_SEND_DEVICE_PARM, request_data)
            await self._transport.write(frame)

            async for parsed_frame in self._download_records():
                if parsed_frame.command_byte in (
                    CommandCode.PCMI_DP_STRING_1,
                    CommandCode.PCMI_DP_STRING_2,
                ):
                    # Determine endianness from command
                    if parsed_frame.command_byte == CommandCode.PCMI_DP_STRING_2:
                        strategy = NON_SWAP_STRATEGY
                    else:
                        strategy = SWAP_STRATEGY

                    reader = HexStringReader(parsed_frame.payload_hex, strategy)
                    header = parse_device_record_header(reader)

                    # Try to get specialized strategy
                    param_strategy = registry.get_parameter_strategy(header.device_type)
                    if param_strategy:
                        device_params = param_strategy.parse(
                            reader, header, parsed_frame.payload_hex
                        )
                    else:
                        device_params = GenericDeviceParameters(
                            header=header,
                            raw_data=parsed_frame.payload_hex,
                        )

                    device_count += 1
                    yield device_params

        finally:
            self._state = ClientState.CONNECTED
            logger.debug("Downloaded %d device parameters", device_count)

    async def download_device_variables(
        self,
        zone_number: int = 0,
    ) -> AsyncGenerator[Any, None]:
        """
        Download device variables (runtime data) from the controller.

        Device variables contain current state and measurements for fans,
        heaters, inlets, sensors, and other devices.

        Args:
            zone_number: Zone to download device variables for (0 = all zones).

        Yields:
            Device variable objects (type varies by device type).
            Use the device registry to get typed device-specific variables.

        Raises:
            ConnectionError: If not connected.
            ProtocolError: If protocol error occurs.

        Example:
            >>> async for device in client.download_device_variables():
            ...     print(f"Device: {device.header.device_type.name}")
        """
        from xtconnect.parsers.device_registry import (
            GenericDeviceVariables,
            create_default_registry,
            parse_device_record_header,
        )
        from xtconnect.parsers.hex_reader import HexStringReader
        from xtconnect.protocol.endianness import NON_SWAP_STRATEGY, SWAP_STRATEGY

        self._ensure_connected()
        self._state = ClientState.DOWNLOADING
        logger.debug("Downloading device variables for zone=%d", zone_number)

        registry = create_default_registry()
        device_count = 0

        try:
            # Build request: command + zone
            request_data = bytes([zone_number])
            frame = self._build_frame(CommandCode.PCMI_SEND_DEVICE_VAR, request_data)
            await self._transport.write(frame)

            async for parsed_frame in self._download_records():
                if parsed_frame.command_byte in (
                    CommandCode.PCMI_DV_STRING_1,
                    CommandCode.PCMI_DV_STRING_2,
                ):
                    # Determine endianness from command
                    if parsed_frame.command_byte == CommandCode.PCMI_DV_STRING_2:
                        strategy = NON_SWAP_STRATEGY
                    else:
                        strategy = SWAP_STRATEGY

                    reader = HexStringReader(parsed_frame.payload_hex, strategy)
                    header = parse_device_record_header(reader)

                    # Try to get specialized strategy
                    var_strategy = registry.get_variable_strategy(header.device_type)
                    if var_strategy:
                        device_vars = var_strategy.parse(
                            reader, header, parsed_frame.payload_hex
                        )
                    else:
                        device_vars = GenericDeviceVariables(
                            header=header,
                            raw_data=parsed_frame.payload_hex,
                        )

                    device_count += 1
                    yield device_vars

        finally:
            self._state = ClientState.CONNECTED
            logger.debug("Downloaded %d device variables", device_count)

    async def _download_records(self) -> AsyncGenerator[ParsedFrame, None]:
        """
        Internal generator for multi-record download sequence.

        Implements the state machine:
        1. Receive data record
        2. Send OK_SEND_NEXT
        3. Repeat until END_OF_RECORD

        Yields:
            ParsedFrame for each data record.
        """
        while True:
            response = await self._transport.read_until(
                ProtocolConstants.ETX,
                self._timeout,
            )

            result, parsed = self._frame_reader.parse(response)

            if result != FrameParseResult.SUCCESS:
                raise ProtocolError(f"Frame parse failed: {result.name}")

            # Check for end of records
            if parsed.command_byte == CommandCode.PCMI_END_OF_RECORD:
                logger.debug("End of record sequence")
                break

            # Check for errors
            if parsed.command_byte in ERROR_CODES:
                if parsed.command_byte == CommandCode.PCMI_ER_NO_ZONE:
                    logger.debug("No more zones")
                    break  # No more zones
                logger.error("Controller error: 0x%02X", parsed.command_byte)
                raise ControllerError(parsed.command_byte)

            # Yield the data frame
            yield parsed

            # Send acknowledgment for next record
            ack_frame = self._build_simple_frame(CommandCode.PCMI_OK_SEND_NEXT)
            await self._transport.write(ack_frame)

    async def _read_response(self, timeout: float | None = None) -> int:
        """
        Read and parse a single-byte response.

        Args:
            timeout: Override timeout in seconds.

        Returns:
            Command/response byte.

        Raises:
            TimeoutError: If no response within timeout.
            ProtocolError: If response is invalid.
        """
        effective_timeout = timeout if timeout is not None else self._timeout

        # First try to read a single byte (for acknowledgments)
        response_byte = await self._transport.read_byte(effective_timeout)

        # Check if it's a single-byte acknowledgment
        if response_byte in ACKNOWLEDGMENT_CODES:
            return response_byte

        # Otherwise, read until CR for framed response
        remaining = await self._transport.read_until(
            ProtocolConstants.ETX,
            effective_timeout,
        )
        full_response = bytes([response_byte]) + remaining

        result, parsed = self._frame_reader.parse(full_response)
        if result != FrameParseResult.SUCCESS:
            raise ProtocolError(f"Invalid response frame: {result.name}")

        return parsed.command_byte

    def _ensure_connected(self) -> None:
        """Verify client is in connected state."""
        if self._state != ClientState.CONNECTED:
            raise ConnectionError(
                f"Not connected (state: {self._state.name})"
            )

    def _build_frame(self, command: int, data: bytes = b"") -> bytes:
        """
        Build a complete protocol frame.

        Frame format: STX + command + data + checksum + ETX

        Args:
            command: Command byte.
            data: Optional data bytes.

        Returns:
            Complete frame bytes.
        """
        payload = bytes([command]) + data
        with_checksum = append_checksum(payload)
        return (
            bytes([ProtocolConstants.STX])
            + with_checksum
            + bytes([ProtocolConstants.ETX])
        )

    def _build_simple_frame(self, command: int) -> bytes:
        """
        Build a simple frame with just command (no data).

        Args:
            command: Command byte.

        Returns:
            Complete frame bytes.
        """
        return self._build_frame(command)

    async def __aenter__(self) -> ControllerClient:
        """Async context manager entry."""
        if not self._transport.is_open:
            await self._transport.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - disconnect and close transport."""
        try:
            if self._state != ClientState.DISCONNECTED:
                await self.disconnect()
        finally:
            if self._transport.is_open:
                await self._transport.close()

    def __repr__(self) -> str:
        sn = self._serial_number or "None"
        return f"ControllerClient(state={self._state.name}, serial={sn})"
