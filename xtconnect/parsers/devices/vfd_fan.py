"""
VFD fan device parsing strategy.

VFD (Variable Frequency Drive) fans are fans with variable speed control.
They provide more precise ventilation control and energy savings compared
to single-speed fans.

Device Type: 26 (VFD_FAN)
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


class VfdFanMode(IntEnum):
    """VFD fan operating modes."""

    OFF = 0
    """Fan is disabled."""

    AUTO = 1
    """Automatic temperature-based speed control."""

    MANUAL = 2
    """Manual speed control."""

    MINIMUM = 3
    """Minimum speed for ventilation."""


class VfdFanStatus(IntEnum):
    """VFD fan runtime status values."""

    OFF = 0
    """Fan is currently off."""

    RUNNING = 1
    """Fan is currently running (variable speed)."""

    RAMPING = 2
    """Fan is ramping up/down to target speed."""

    INHIBITED = 3
    """Fan is inhibited by temperature or interlock."""

    FAULT = 4
    """Fan has a fault condition (VFD error)."""


@dataclass(frozen=True)
class VfdFanParameters:
    """
    VFD fan device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        on_temp_offset: Temperature offset to start fan.
        min_speed: Minimum speed when running (0-100%).
        max_speed: Maximum speed (0-100%).
        speed_per_degree: Speed change per degree of temperature.
        ramp_time: Time to ramp between speeds in seconds.
        min_on_time: Minimum on time in seconds.
        min_off_time: Minimum off time in seconds.
        mode: Operating mode (auto, manual, minimum).
        cfm_at_100: CFM rating at 100% speed.
        control_bits: Control configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    on_temp_offset: Temperature
    min_speed: int
    max_speed: int
    speed_per_degree: int
    ramp_time: int
    min_on_time: int
    min_off_time: int
    mode: int
    cfm_at_100: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.VFD_FAN

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def vfd_fan_mode(self) -> VfdFanMode:
        """Get the fan mode as enum."""
        try:
            return VfdFanMode(self.mode)
        except ValueError:
            return VfdFanMode.OFF


@dataclass(frozen=True)
class VfdFanVariables:
    """
    VFD fan device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        current_speed: Current speed (0-100%).
        target_speed: Target speed (0-100%).
        runtime_today: Total runtime today in minutes.
        runtime_total: Total runtime in hours (lifetime).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    current_speed: int
    target_speed: int
    runtime_today: int
    runtime_total: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.VFD_FAN

    @property
    def vfd_fan_status(self) -> VfdFanStatus:
        """Get the fan status as enum."""
        try:
            return VfdFanStatus(self.status)
        except ValueError:
            return VfdFanStatus.OFF

    @property
    def is_running(self) -> bool:
        """Check if fan is currently running."""
        return self.status in (VfdFanStatus.RUNNING, VfdFanStatus.RAMPING)

    @property
    def is_at_target(self) -> bool:
        """Check if fan is at target speed."""
        return self.current_speed == self.target_speed

    @property
    def estimated_cfm(self) -> int:
        """Estimate current CFM based on speed (linear approximation)."""
        # Note: Actual CFM curve may not be linear
        return 0  # Would need CFM rating to calculate


class VfdFanParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for VFD fan parameters.

    VFD fan parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - On temp offset (2 bytes, int16)
    - Min speed (1 byte, %)
    - Max speed (1 byte, %)
    - Speed per degree (1 byte, %)
    - Reserved (1 byte)
    - Ramp time (2 bytes, seconds)
    - Min on time (2 bytes, seconds)
    - Min off time (2 bytes, seconds)
    - Mode (1 byte)
    - Reserved (1 byte)
    - CFM at 100% (2 bytes)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns VFD_FAN device type."""
        return DeviceType.VFD_FAN

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> VfdFanParameters:
        """Parse VFD fan parameters from hex data."""
        name_index = reader.read_uint16()
        on_temp_offset = Temperature(raw_value=reader.read_int16())
        min_speed = reader.read_byte()
        max_speed = reader.read_byte()
        speed_per_degree = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        ramp_time = reader.read_uint16()
        min_on_time = reader.read_uint16()
        min_off_time = reader.read_uint16()
        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        cfm_at_100 = reader.read_uint16()
        control_bits = reader.read_uint16()

        return VfdFanParameters(
            header=header,
            name_index=name_index,
            on_temp_offset=on_temp_offset,
            min_speed=min_speed,
            max_speed=max_speed,
            speed_per_degree=speed_per_degree,
            ramp_time=ramp_time,
            min_on_time=min_on_time,
            min_off_time=min_off_time,
            mode=mode,
            cfm_at_100=cfm_at_100,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class VfdFanVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for VFD fan variables.

    VFD fan variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current speed (1 byte, %)
    - Target speed (1 byte, %)
    - Runtime today (2 bytes, minutes)
    - Runtime total (2 bytes, hours)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns VFD_FAN device type."""
        return DeviceType.VFD_FAN

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> VfdFanVariables:
        """Parse VFD fan variables from hex data."""
        status = reader.read_uint16()
        current_speed = reader.read_byte()
        target_speed = reader.read_byte()
        runtime_today = reader.read_uint16()
        runtime_total = reader.read_uint16()

        return VfdFanVariables(
            header=header,
            status=status,
            current_speed=current_speed,
            target_speed=target_speed,
            runtime_today=runtime_today,
            runtime_total=runtime_total,
            raw_data=raw_data,
        )
