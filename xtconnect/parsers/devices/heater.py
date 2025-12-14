"""
Heater device parsing strategy.

Heaters control heating equipment and activate based on temperature.
They typically turn on when temperature drops below setpoint and
turn off when it rises above.

Device Type: 6 (HEATER)
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


class HeaterMode(IntEnum):
    """Heater operating modes."""

    OFF = 0
    """Heater is disabled."""

    AUTO = 1
    """Automatic temperature-based control."""

    ON = 2
    """Heater is forced on."""


class HeaterStatus(IntEnum):
    """Heater runtime status values."""

    OFF = 0
    """Heater is currently off."""

    RUNNING = 1
    """Heater is currently running."""

    DELAY = 2
    """Heater is in delay period."""

    INHIBITED = 3
    """Heater is inhibited by temperature or interlock."""


@dataclass(frozen=True)
class HeaterParameters:
    """
    Heater device parameters.

    Contains configuration for heater operation including temperature
    thresholds and timing parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        on_temp_offset: Temperature offset below setpoint to turn on.
        off_temp_offset: Temperature offset above setpoint to turn off.
        min_on_time: Minimum on time in seconds.
        min_off_time: Minimum off time in seconds.
        mode: Operating mode (auto, on, off).
        btu_rating: BTU rating of the heater.
        control_bits: Control configuration flags.
        interlock_bits: Interlock configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    on_temp_offset: Temperature
    off_temp_offset: Temperature
    min_on_time: int
    min_off_time: int
    mode: int
    btu_rating: int
    control_bits: int
    interlock_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.HEATER

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def heater_mode(self) -> HeaterMode:
        """Get the heater mode as enum."""
        try:
            return HeaterMode(self.mode)
        except ValueError:
            return HeaterMode.OFF

    @property
    def is_auto_mode(self) -> bool:
        """Check if heater is in automatic mode."""
        return self.mode == HeaterMode.AUTO


@dataclass(frozen=True)
class HeaterVariables:
    """
    Heater device variables (runtime data).

    Contains the current operating state and runtime counters.

    Attributes:
        header: Common device record header.
        status: Current operating status.
        runtime_today: Total runtime today in minutes.
        runtime_total: Total runtime in hours (lifetime).
        cycles_today: Number of on/off cycles today.
        fuel_usage_today: Fuel usage today (units depend on heater type).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    runtime_today: int
    runtime_total: int
    cycles_today: int
    fuel_usage_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.HEATER

    @property
    def heater_status(self) -> HeaterStatus:
        """Get the heater status as enum."""
        try:
            return HeaterStatus(self.status)
        except ValueError:
            return HeaterStatus.OFF

    @property
    def is_running(self) -> bool:
        """Check if heater is currently running."""
        return self.status == HeaterStatus.RUNNING

    @property
    def is_off(self) -> bool:
        """Check if heater is currently off."""
        return self.status == HeaterStatus.OFF


class HeaterParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for heater parameters.

    Heater parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - On temp offset (2 bytes, int16)
    - Off temp offset (2 bytes, int16)
    - Min on time (2 bytes)
    - Min off time (2 bytes)
    - Mode (1 byte)
    - Reserved (1 byte)
    - BTU rating (4 bytes, uint32)
    - Control bits (2 bytes)
    - Interlock bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns HEATER device type."""
        return DeviceType.HEATER

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> HeaterParameters:
        """
        Parse heater parameters from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed HeaterParameters.
        """
        name_index = reader.read_uint16()

        on_temp_offset = Temperature(raw_value=reader.read_int16())
        off_temp_offset = Temperature(raw_value=reader.read_int16())

        min_on_time = reader.read_uint16()
        min_off_time = reader.read_uint16()

        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        btu_rating = reader.read_uint32()
        control_bits = reader.read_uint16()
        interlock_bits = reader.read_uint16()

        return HeaterParameters(
            header=header,
            name_index=name_index,
            on_temp_offset=on_temp_offset,
            off_temp_offset=off_temp_offset,
            min_on_time=min_on_time,
            min_off_time=min_off_time,
            mode=mode,
            btu_rating=btu_rating,
            control_bits=control_bits,
            interlock_bits=interlock_bits,
            raw_data=raw_data,
        )


class HeaterVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for heater variables.

    Heater variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Runtime today (2 bytes, minutes)
    - Runtime total (2 bytes, hours)
    - Cycles today (2 bytes)
    - Fuel usage today (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns HEATER device type."""
        return DeviceType.HEATER

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> HeaterVariables:
        """
        Parse heater variables from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed HeaterVariables.
        """
        status = reader.read_uint16()
        runtime_today = reader.read_uint16()
        runtime_total = reader.read_uint16()
        cycles_today = reader.read_uint16()
        fuel_usage_today = reader.read_uint16()

        return HeaterVariables(
            header=header,
            status=status,
            runtime_today=runtime_today,
            runtime_total=runtime_total,
            cycles_today=cycles_today,
            fuel_usage_today=fuel_usage_today,
            raw_data=raw_data,
        )
