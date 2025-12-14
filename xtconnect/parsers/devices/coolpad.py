"""
Cool pad device parsing strategy.

Cool pads are evaporative cooling systems that cool air by passing it
through water-saturated pads. They work best in dry climates and are
controlled based on temperature.

Device Type: 7 (COOLPAD)
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


class CoolPadMode(IntEnum):
    """Cool pad operating modes."""

    OFF = 0
    """Cool pad is disabled."""

    AUTO = 1
    """Automatic temperature-based control."""

    ON = 2
    """Cool pad is always on."""

    TIMER = 3
    """Timer-based cycling."""


class CoolPadStatus(IntEnum):
    """Cool pad runtime status values."""

    OFF = 0
    """Cool pad is currently off."""

    RUNNING = 1
    """Cool pad is currently running."""

    PURGE = 2
    """Cool pad is in purge cycle (draining)."""

    DELAY = 3
    """Cool pad is in delay period."""

    INHIBITED = 4
    """Cool pad is inhibited by temperature or humidity."""


@dataclass(frozen=True)
class CoolPadParameters:
    """
    Cool pad device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        on_temp_offset: Temperature offset above setpoint to turn on.
        off_temp_offset: Temperature offset to turn off.
        min_on_time: Minimum on time in seconds.
        min_off_time: Minimum off time in seconds.
        purge_time: Purge cycle duration in seconds.
        purge_interval: Time between purge cycles in minutes.
        mode: Operating mode (auto, on, off, timer).
        humidity_lockout: Humidity level to disable cooling (%).
        control_bits: Control configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    on_temp_offset: Temperature
    off_temp_offset: Temperature
    min_on_time: int
    min_off_time: int
    purge_time: int
    purge_interval: int
    mode: int
    humidity_lockout: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.COOLPAD

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def coolpad_mode(self) -> CoolPadMode:
        """Get the cool pad mode as enum."""
        try:
            return CoolPadMode(self.mode)
        except ValueError:
            return CoolPadMode.OFF


@dataclass(frozen=True)
class CoolPadVariables:
    """
    Cool pad device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        runtime_today: Total runtime today in minutes.
        cycles_today: Number of on/off cycles today.
        water_usage_today: Water usage today in gallons.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    runtime_today: int
    cycles_today: int
    water_usage_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.COOLPAD

    @property
    def coolpad_status(self) -> CoolPadStatus:
        """Get the cool pad status as enum."""
        try:
            return CoolPadStatus(self.status)
        except ValueError:
            return CoolPadStatus.OFF

    @property
    def is_running(self) -> bool:
        """Check if cool pad is currently running."""
        return self.status == CoolPadStatus.RUNNING

    @property
    def is_purging(self) -> bool:
        """Check if cool pad is in purge cycle."""
        return self.status == CoolPadStatus.PURGE


class CoolPadParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for cool pad parameters.

    Cool pad parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - On temp offset (2 bytes, int16)
    - Off temp offset (2 bytes, int16)
    - Min on time (2 bytes, seconds)
    - Min off time (2 bytes, seconds)
    - Purge time (2 bytes, seconds)
    - Purge interval (2 bytes, minutes)
    - Mode (1 byte)
    - Humidity lockout (1 byte, %)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns COOLPAD device type."""
        return DeviceType.COOLPAD

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> CoolPadParameters:
        """Parse cool pad parameters from hex data."""
        name_index = reader.read_uint16()
        on_temp_offset = Temperature(raw_value=reader.read_int16())
        off_temp_offset = Temperature(raw_value=reader.read_int16())
        min_on_time = reader.read_uint16()
        min_off_time = reader.read_uint16()
        purge_time = reader.read_uint16()
        purge_interval = reader.read_uint16()
        mode = reader.read_byte()
        humidity_lockout = reader.read_byte()
        control_bits = reader.read_uint16()

        return CoolPadParameters(
            header=header,
            name_index=name_index,
            on_temp_offset=on_temp_offset,
            off_temp_offset=off_temp_offset,
            min_on_time=min_on_time,
            min_off_time=min_off_time,
            purge_time=purge_time,
            purge_interval=purge_interval,
            mode=mode,
            humidity_lockout=humidity_lockout,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class CoolPadVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for cool pad variables.

    Cool pad variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Runtime today (2 bytes, minutes)
    - Cycles today (2 bytes)
    - Water usage today (2 bytes, gallons)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns COOLPAD device type."""
        return DeviceType.COOLPAD

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> CoolPadVariables:
        """Parse cool pad variables from hex data."""
        status = reader.read_uint16()
        runtime_today = reader.read_uint16()
        cycles_today = reader.read_uint16()
        water_usage_today = reader.read_uint16()

        return CoolPadVariables(
            header=header,
            status=status,
            runtime_today=runtime_today,
            cycles_today=cycles_today,
            water_usage_today=water_usage_today,
            raw_data=raw_data,
        )
