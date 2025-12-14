"""
Ridge vent device parsing strategy.

Ridge vents are roof-mounted ventilation openings that provide natural
air exhaust. They operate based on temperature and can be affected by
wind conditions.

Device Type: 5 (RIDGE_VENT)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from xtconnect.models.records import DeviceRecordHeader, DeviceType, Temperature
from xtconnect.parsers.device_registry import (
    DeviceParameterStrategy,
    DeviceVariableStrategy,
)

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader


class RidgeVentControlMode(IntEnum):
    """Ridge vent control modes."""

    OFF = 0
    """Vent is disabled (closed)."""

    TEMPERATURE = 1
    """Controlled by temperature."""

    MANUAL = 2
    """Manual position control."""


class RidgeVentStatus(IntEnum):
    """Ridge vent runtime status values."""

    STOPPED = 0
    """Vent is not moving."""

    OPENING = 1
    """Vent is opening."""

    CLOSING = 2
    """Vent is closing."""

    AT_TARGET = 3
    """Vent is at target position."""

    FAULT = 4
    """Vent has a fault condition."""


@dataclass(frozen=True)
class RidgeVentParameters:
    """
    Ridge vent device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        min_position: Minimum allowed position (0-100%).
        max_position: Maximum allowed position (0-100%).
        open_time: Time to fully open in seconds.
        close_time: Time to fully close in seconds.
        control_mode: Control mode (temperature or manual).
        temp_offset: Temperature offset for position calculation.
        position_per_degree: Position change per degree of temperature offset.
        control_bits: Control configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    min_position: int
    max_position: int
    open_time: int
    close_time: int
    control_mode: int
    temp_offset: Temperature
    position_per_degree: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.RIDGE_VENT

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def ridge_vent_control_mode(self) -> RidgeVentControlMode:
        """Get the control mode as enum."""
        try:
            return RidgeVentControlMode(self.control_mode)
        except ValueError:
            return RidgeVentControlMode.OFF


@dataclass(frozen=True)
class RidgeVentVariables:
    """
    Ridge vent device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        current_position: Current position (0-100%).
        target_position: Target position (0-100%).
        runtime_today: Total motor runtime today in seconds.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    current_position: int
    target_position: int
    runtime_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.RIDGE_VENT

    @property
    def ridge_vent_status(self) -> RidgeVentStatus:
        """Get the ridge vent status as enum."""
        try:
            return RidgeVentStatus(self.status)
        except ValueError:
            return RidgeVentStatus.STOPPED

    @property
    def is_moving(self) -> bool:
        """Check if vent is currently moving."""
        return self.status in (RidgeVentStatus.OPENING, RidgeVentStatus.CLOSING)


class RidgeVentParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for ridge vent parameters.

    Ridge vent parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Min position (1 byte, %)
    - Max position (1 byte, %)
    - Open time (2 bytes, seconds)
    - Close time (2 bytes, seconds)
    - Control mode (1 byte)
    - Reserved (1 byte)
    - Temp offset (2 bytes, int16)
    - Position per degree (1 byte, %)
    - Reserved (1 byte)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns RIDGE_VENT device type."""
        return DeviceType.RIDGE_VENT

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> RidgeVentParameters:
        """Parse ridge vent parameters from hex data."""
        name_index = reader.read_uint16()
        min_position = reader.read_byte()
        max_position = reader.read_byte()
        open_time = reader.read_uint16()
        close_time = reader.read_uint16()
        control_mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        temp_offset = Temperature(raw_value=reader.read_int16())
        position_per_degree = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        control_bits = reader.read_uint16()

        return RidgeVentParameters(
            header=header,
            name_index=name_index,
            min_position=min_position,
            max_position=max_position,
            open_time=open_time,
            close_time=close_time,
            control_mode=control_mode,
            temp_offset=temp_offset,
            position_per_degree=position_per_degree,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class RidgeVentVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for ridge vent variables.

    Ridge vent variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current position (1 byte, %)
    - Target position (1 byte, %)
    - Runtime today (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns RIDGE_VENT device type."""
        return DeviceType.RIDGE_VENT

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> RidgeVentVariables:
        """Parse ridge vent variables from hex data."""
        status = reader.read_uint16()
        current_position = reader.read_byte()
        target_position = reader.read_byte()
        runtime_today = reader.read_uint16()

        return RidgeVentVariables(
            header=header,
            status=status,
            current_position=current_position,
            target_position=target_position,
            runtime_today=runtime_today,
            raw_data=raw_data,
        )
