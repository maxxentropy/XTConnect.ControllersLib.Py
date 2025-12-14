"""
Curtain device parsing strategy.

Curtains are side curtain ventilation systems that can open and close
to provide natural ventilation. They're similar to inlets but typically
larger and may have different control characteristics.

Device Type: 4 (CURTAIN)
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


class CurtainControlMode(IntEnum):
    """Curtain control modes."""

    OFF = 0
    """Curtain is disabled (closed)."""

    TEMPERATURE = 1
    """Controlled by temperature."""

    STATIC_PRESSURE = 2
    """Controlled by static pressure."""

    COMBINED = 3
    """Controlled by both temperature and static pressure."""

    MANUAL = 4
    """Manual position control."""

    WIND = 5
    """Controlled by wind conditions."""


class CurtainStatus(IntEnum):
    """Curtain runtime status values."""

    STOPPED = 0
    """Curtain is not moving."""

    OPENING = 1
    """Curtain is opening."""

    CLOSING = 2
    """Curtain is closing."""

    AT_TARGET = 3
    """Curtain is at target position."""

    WIND_CLOSE = 4
    """Curtain closed due to wind."""

    FAULT = 5
    """Curtain has a fault condition."""


@dataclass(frozen=True)
class CurtainParameters:
    """
    Curtain device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        min_position: Minimum allowed position (0-100%).
        max_position: Maximum allowed position (0-100%).
        open_time: Time to fully open in seconds.
        close_time: Time to fully close in seconds.
        control_mode: Control mode (temperature, static, combined, manual, wind).
        static_setpoint: Static pressure setpoint (hundredths of inch WC).
        temp_offset: Temperature offset for position calculation.
        position_per_degree: Position change per degree of temperature offset.
        wind_close_speed: Wind speed threshold to close (mph).
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
    wind_close_speed: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.CURTAIN

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def curtain_control_mode(self) -> CurtainControlMode:
        """Get the control mode as enum."""
        try:
            return CurtainControlMode(self.control_mode)
        except ValueError:
            return CurtainControlMode.OFF


@dataclass(frozen=True)
class CurtainVariables:
    """
    Curtain device variables (runtime data).

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
        return DeviceType.CURTAIN

    @property
    def curtain_status(self) -> CurtainStatus:
        """Get the curtain status as enum."""
        try:
            return CurtainStatus(self.status)
        except ValueError:
            return CurtainStatus.STOPPED

    @property
    def is_moving(self) -> bool:
        """Check if curtain is currently moving."""
        return self.status in (CurtainStatus.OPENING, CurtainStatus.CLOSING)

    @property
    def is_open(self) -> bool:
        """Check if curtain is fully open (>= 95%)."""
        return self.current_position >= 95

    @property
    def is_closed(self) -> bool:
        """Check if curtain is fully closed (<= 5%)."""
        return self.current_position <= 5


class CurtainParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for curtain parameters.

    Curtain parameter record structure (after 8-byte header):
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
    - Wind close speed (1 byte, mph)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns CURTAIN device type."""
        return DeviceType.CURTAIN

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> CurtainParameters:
        """Parse curtain parameters from hex data."""
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
        wind_close_speed = reader.read_byte()
        control_bits = reader.read_uint16()

        return CurtainParameters(
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
            wind_close_speed=wind_close_speed,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class CurtainVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for curtain variables.

    Curtain variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current position (1 byte, %)
    - Target position (1 byte, %)
    - Runtime today (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns CURTAIN device type."""
        return DeviceType.CURTAIN

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> CurtainVariables:
        """Parse curtain variables from hex data."""
        status = reader.read_uint16()
        current_position = reader.read_byte()
        target_position = reader.read_byte()
        runtime_today = reader.read_uint16()

        return CurtainVariables(
            header=header,
            status=status,
            current_position=current_position,
            target_position=target_position,
            runtime_today=runtime_today,
            raw_data=raw_data,
        )
