"""
Chimney device parsing strategy.

Chimneys are natural ventilation devices that use thermal buoyancy
for exhaust. They can be opened/closed based on temperature and
work with minimum ventilation systems.

Device Type: 15 (CHIMNEY)
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


class ChimneyControlMode(IntEnum):
    """Chimney control modes."""

    OFF = 0
    """Chimney is disabled (closed)."""

    TEMPERATURE = 1
    """Controlled by temperature."""

    MINIMUM_VENT = 2
    """Controlled by minimum ventilation requirements."""

    MANUAL = 3
    """Manual position control."""


class ChimneyStatus(IntEnum):
    """Chimney runtime status values."""

    STOPPED = 0
    """Chimney is not moving."""

    OPENING = 1
    """Chimney is opening."""

    CLOSING = 2
    """Chimney is closing."""

    AT_TARGET = 3
    """Chimney is at target position."""


@dataclass(frozen=True)
class ChimneyParameters:
    """
    Chimney device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        min_position: Minimum allowed position (0-100%).
        max_position: Maximum allowed position (0-100%).
        open_time: Time to fully open in seconds.
        close_time: Time to fully close in seconds.
        control_mode: Control mode (temperature, min vent, manual).
        temp_offset: Temperature offset for position calculation.
        position_per_degree: Position change per degree of temperature offset.
        min_vent_position: Position for minimum ventilation mode.
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
    min_vent_position: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.CHIMNEY

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def chimney_control_mode(self) -> ChimneyControlMode:
        """Get the control mode as enum."""
        try:
            return ChimneyControlMode(self.control_mode)
        except ValueError:
            return ChimneyControlMode.OFF


@dataclass(frozen=True)
class ChimneyVariables:
    """
    Chimney device variables (runtime data).

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
        return DeviceType.CHIMNEY

    @property
    def chimney_status(self) -> ChimneyStatus:
        """Get the chimney status as enum."""
        try:
            return ChimneyStatus(self.status)
        except ValueError:
            return ChimneyStatus.STOPPED

    @property
    def is_moving(self) -> bool:
        """Check if chimney is currently moving."""
        return self.status in (ChimneyStatus.OPENING, ChimneyStatus.CLOSING)


class ChimneyParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for chimney parameters.

    Chimney parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Min position (1 byte, %)
    - Max position (1 byte, %)
    - Open time (2 bytes, seconds)
    - Close time (2 bytes, seconds)
    - Control mode (1 byte)
    - Reserved (1 byte)
    - Temp offset (2 bytes, int16)
    - Position per degree (1 byte, %)
    - Min vent position (1 byte, %)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns CHIMNEY device type."""
        return DeviceType.CHIMNEY

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> ChimneyParameters:
        """Parse chimney parameters from hex data."""
        name_index = reader.read_uint16()
        min_position = reader.read_byte()
        max_position = reader.read_byte()
        open_time = reader.read_uint16()
        close_time = reader.read_uint16()
        control_mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        temp_offset = Temperature(raw_value=reader.read_int16())
        position_per_degree = reader.read_byte()
        min_vent_position = reader.read_byte()
        control_bits = reader.read_uint16()

        return ChimneyParameters(
            header=header,
            name_index=name_index,
            min_position=min_position,
            max_position=max_position,
            open_time=open_time,
            close_time=close_time,
            control_mode=control_mode,
            temp_offset=temp_offset,
            position_per_degree=position_per_degree,
            min_vent_position=min_vent_position,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class ChimneyVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for chimney variables.

    Chimney variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current position (1 byte, %)
    - Target position (1 byte, %)
    - Runtime today (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns CHIMNEY device type."""
        return DeviceType.CHIMNEY

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> ChimneyVariables:
        """Parse chimney variables from hex data."""
        status = reader.read_uint16()
        current_position = reader.read_byte()
        target_position = reader.read_byte()
        runtime_today = reader.read_uint16()

        return ChimneyVariables(
            header=header,
            status=status,
            current_position=current_position,
            target_position=target_position,
            runtime_today=runtime_today,
            raw_data=raw_data,
        )
