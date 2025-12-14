"""
Timed device parsing strategy.

Timed devices are timer-controlled outputs for lights, feeders, and
other equipment that operates on a schedule. They support multiple
on/off times and can be synchronized with other devices.

Device Type: 9 (TIMED)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from xtconnect.models.records import DeviceRecordHeader, DeviceType
from xtconnect.parsers.device_registry import (
    DeviceParameterStrategy,
    DeviceVariableStrategy,
)

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader


class TimedMode(IntEnum):
    """Timed device operating modes."""

    OFF = 0
    """Device is disabled."""

    AUTO = 1
    """Automatic timer-based control."""

    ON = 2
    """Device is always on."""

    CYCLE = 3
    """Cycling on/off at fixed intervals."""


class TimedStatus(IntEnum):
    """Timed device runtime status values."""

    OFF = 0
    """Device is currently off."""

    ON = 1
    """Device is currently on (timer active)."""

    CYCLE_ON = 2
    """Device is on in cycle mode."""

    CYCLE_OFF = 3
    """Device is off in cycle mode."""


@dataclass(frozen=True)
class TimedParameters:
    """
    Timed device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        on_time_1: First on time (minutes from midnight).
        off_time_1: First off time (minutes from midnight).
        on_time_2: Second on time (minutes from midnight).
        off_time_2: Second off time (minutes from midnight).
        cycle_on_time: Cycle mode on duration in seconds.
        cycle_off_time: Cycle mode off duration in seconds.
        mode: Operating mode (off, auto, on, cycle).
        control_bits: Control configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    on_time_1: int
    off_time_1: int
    on_time_2: int
    off_time_2: int
    cycle_on_time: int
    cycle_off_time: int
    mode: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.TIMED

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def timed_mode(self) -> TimedMode:
        """Get the timed mode as enum."""
        try:
            return TimedMode(self.mode)
        except ValueError:
            return TimedMode.OFF

    def format_time(self, minutes_from_midnight: int) -> str:
        """Format time value as HH:MM string."""
        if minutes_from_midnight < 0 or minutes_from_midnight >= 1440:
            return "--:--"
        hours = minutes_from_midnight // 60
        mins = minutes_from_midnight % 60
        return f"{hours:02d}:{mins:02d}"


@dataclass(frozen=True)
class TimedVariables:
    """
    Timed device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        runtime_today: Total runtime today in minutes.
        cycles_today: Number of on/off cycles today.
        time_until_next: Time until next state change in minutes.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    runtime_today: int
    cycles_today: int
    time_until_next: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.TIMED

    @property
    def timed_status(self) -> TimedStatus:
        """Get the timed status as enum."""
        try:
            return TimedStatus(self.status)
        except ValueError:
            return TimedStatus.OFF

    @property
    def is_on(self) -> bool:
        """Check if device is currently on."""
        return self.status in (TimedStatus.ON, TimedStatus.CYCLE_ON)


class TimedParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for timed device parameters.

    Timed parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - On time 1 (2 bytes, minutes from midnight)
    - Off time 1 (2 bytes, minutes from midnight)
    - On time 2 (2 bytes, minutes from midnight)
    - Off time 2 (2 bytes, minutes from midnight)
    - Cycle on time (2 bytes, seconds)
    - Cycle off time (2 bytes, seconds)
    - Mode (1 byte)
    - Reserved (1 byte)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns TIMED device type."""
        return DeviceType.TIMED

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> TimedParameters:
        """Parse timed device parameters from hex data."""
        name_index = reader.read_uint16()
        on_time_1 = reader.read_uint16()
        off_time_1 = reader.read_uint16()
        on_time_2 = reader.read_uint16()
        off_time_2 = reader.read_uint16()
        cycle_on_time = reader.read_uint16()
        cycle_off_time = reader.read_uint16()
        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        control_bits = reader.read_uint16()

        return TimedParameters(
            header=header,
            name_index=name_index,
            on_time_1=on_time_1,
            off_time_1=off_time_1,
            on_time_2=on_time_2,
            off_time_2=off_time_2,
            cycle_on_time=cycle_on_time,
            cycle_off_time=cycle_off_time,
            mode=mode,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class TimedVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for timed device variables.

    Timed variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Runtime today (2 bytes, minutes)
    - Cycles today (2 bytes)
    - Time until next (2 bytes, minutes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns TIMED device type."""
        return DeviceType.TIMED

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> TimedVariables:
        """Parse timed device variables from hex data."""
        status = reader.read_uint16()
        runtime_today = reader.read_uint16()
        cycles_today = reader.read_uint16()
        time_until_next = reader.read_uint16()

        return TimedVariables(
            header=header,
            status=status,
            runtime_today=runtime_today,
            cycles_today=cycles_today,
            time_until_next=time_until_next,
            raw_data=raw_data,
        )
