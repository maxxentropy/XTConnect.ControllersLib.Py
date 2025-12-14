"""
Inlet device parsing strategy.

Inlets are positional devices that control ventilation openings.
They have a target position (0-100%) and can be controlled based
on temperature, static pressure, or both.

Device Type: 3 (INLET)
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


class InletControlMode(IntEnum):
    """Inlet control modes."""

    OFF = 0
    """Inlet is disabled (closed)."""

    TEMPERATURE = 1
    """Controlled by temperature."""

    STATIC_PRESSURE = 2
    """Controlled by static pressure."""

    COMBINED = 3
    """Controlled by both temperature and static pressure."""

    MANUAL = 4
    """Manual position control."""


class InletStatus(IntEnum):
    """Inlet runtime status values."""

    STOPPED = 0
    """Inlet is not moving."""

    OPENING = 1
    """Inlet is opening."""

    CLOSING = 2
    """Inlet is closing."""

    AT_TARGET = 3
    """Inlet is at target position."""

    FAULT = 4
    """Inlet has a fault condition."""


@dataclass(frozen=True)
class InletParameters:
    """
    Inlet device parameters.

    Contains configuration for inlet position control including
    limits, timing, and control mode settings.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        min_position: Minimum allowed position (0-100%).
        max_position: Maximum allowed position (0-100%).
        open_time: Time to fully open in seconds.
        close_time: Time to fully close in seconds.
        control_mode: Control mode (temperature, static, combined, manual).
        static_setpoint: Static pressure setpoint (hundredths of inch WC).
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
    static_setpoint: int
    temp_offset: Temperature
    position_per_degree: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.INLET

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def inlet_control_mode(self) -> InletControlMode:
        """Get the control mode as enum."""
        try:
            return InletControlMode(self.control_mode)
        except ValueError:
            return InletControlMode.OFF

    @property
    def uses_temperature_control(self) -> bool:
        """Check if inlet uses temperature-based control."""
        return self.control_mode in (
            InletControlMode.TEMPERATURE,
            InletControlMode.COMBINED,
        )

    @property
    def uses_static_control(self) -> bool:
        """Check if inlet uses static pressure control."""
        return self.control_mode in (
            InletControlMode.STATIC_PRESSURE,
            InletControlMode.COMBINED,
        )


@dataclass(frozen=True)
class InletVariables:
    """
    Inlet device variables (runtime data).

    Contains the current position and operating state.

    Attributes:
        header: Common device record header.
        status: Current operating status.
        current_position: Current position (0-100%).
        target_position: Target position (0-100%).
        static_reading: Current static pressure reading.
        runtime_today: Total motor runtime today in seconds.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    current_position: int
    target_position: int
    static_reading: int
    runtime_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.INLET

    @property
    def inlet_status(self) -> InletStatus:
        """Get the inlet status as enum."""
        try:
            return InletStatus(self.status)
        except ValueError:
            return InletStatus.STOPPED

    @property
    def is_moving(self) -> bool:
        """Check if inlet is currently moving."""
        return self.status in (InletStatus.OPENING, InletStatus.CLOSING)

    @property
    def is_at_target(self) -> bool:
        """Check if inlet has reached target position."""
        return self.status == InletStatus.AT_TARGET

    @property
    def is_open(self) -> bool:
        """Check if inlet is fully open (>= 95%)."""
        return self.current_position >= 95

    @property
    def is_closed(self) -> bool:
        """Check if inlet is fully closed (<= 5%)."""
        return self.current_position <= 5

    @property
    def position_error(self) -> int:
        """Get difference between target and current position."""
        return self.target_position - self.current_position


class InletParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for inlet parameters.

    Inlet parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Min position (1 byte, %)
    - Max position (1 byte, %)
    - Open time (2 bytes, seconds)
    - Close time (2 bytes, seconds)
    - Control mode (1 byte)
    - Reserved (1 byte)
    - Static setpoint (2 bytes, hundredths inch WC)
    - Temp offset (2 bytes, int16)
    - Position per degree (1 byte, %)
    - Reserved (1 byte)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns INLET device type."""
        return DeviceType.INLET

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> InletParameters:
        """
        Parse inlet parameters from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed InletParameters.
        """
        name_index = reader.read_uint16()

        min_position = reader.read_byte()
        max_position = reader.read_byte()

        open_time = reader.read_uint16()
        close_time = reader.read_uint16()

        control_mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        static_setpoint = reader.read_uint16()
        temp_offset = Temperature(raw_value=reader.read_int16())

        position_per_degree = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        control_bits = reader.read_uint16()

        return InletParameters(
            header=header,
            name_index=name_index,
            min_position=min_position,
            max_position=max_position,
            open_time=open_time,
            close_time=close_time,
            control_mode=control_mode,
            static_setpoint=static_setpoint,
            temp_offset=temp_offset,
            position_per_degree=position_per_degree,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class InletVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for inlet variables.

    Inlet variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current position (1 byte, %)
    - Target position (1 byte, %)
    - Static reading (2 bytes, hundredths inch WC)
    - Runtime today (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns INLET device type."""
        return DeviceType.INLET

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> InletVariables:
        """
        Parse inlet variables from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed InletVariables.
        """
        status = reader.read_uint16()
        current_position = reader.read_byte()
        target_position = reader.read_byte()
        static_reading = reader.read_uint16()
        runtime_today = reader.read_uint16()

        return InletVariables(
            header=header,
            status=status,
            current_position=current_position,
            target_position=target_position,
            static_reading=static_reading,
            runtime_today=runtime_today,
            raw_data=raw_data,
        )
