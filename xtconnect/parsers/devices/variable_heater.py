"""
Variable heater device parsing strategy.

Variable heaters are modulating heaters that can operate at different
output levels (0-100%) rather than simple on/off. They provide more
precise temperature control and energy efficiency.

Device Type: 25 (VARIABLE_HEATER)
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


class VariableHeaterMode(IntEnum):
    """Variable heater operating modes."""

    OFF = 0
    """Heater is disabled."""

    AUTO = 1
    """Automatic temperature-based modulating control."""

    MANUAL = 2
    """Manual output level control."""

    MINIMUM = 3
    """Minimum fire rate."""


class VariableHeaterStatus(IntEnum):
    """Variable heater runtime status values."""

    OFF = 0
    """Heater is currently off."""

    RUNNING = 1
    """Heater is currently running (modulating)."""

    DELAY = 2
    """Heater is in delay period."""

    INHIBITED = 3
    """Heater is inhibited by temperature or interlock."""

    FAULT = 4
    """Heater has a fault condition."""


@dataclass(frozen=True)
class VariableHeaterParameters:
    """
    Variable heater device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        on_temp_offset: Temperature offset below setpoint to start.
        off_temp_offset: Temperature offset above setpoint to stop.
        min_fire_rate: Minimum fire rate (0-100%).
        max_fire_rate: Maximum fire rate (0-100%).
        degrees_per_percent: Temperature change per percent output.
        min_on_time: Minimum on time in seconds.
        min_off_time: Minimum off time in seconds.
        mode: Operating mode (auto, manual, minimum).
        btu_rating: BTU rating of the heater.
        control_bits: Control configuration flags.
        interlock_bits: Interlock configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    on_temp_offset: Temperature
    off_temp_offset: Temperature
    min_fire_rate: int
    max_fire_rate: int
    degrees_per_percent: int
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
        return DeviceType.VARIABLE_HEATER

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def variable_heater_mode(self) -> VariableHeaterMode:
        """Get the heater mode as enum."""
        try:
            return VariableHeaterMode(self.mode)
        except ValueError:
            return VariableHeaterMode.OFF


@dataclass(frozen=True)
class VariableHeaterVariables:
    """
    Variable heater device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        current_output: Current output level (0-100%).
        target_output: Target output level (0-100%).
        runtime_today: Total runtime today in minutes.
        fuel_usage_today: Fuel usage today (units depend on heater type).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    current_output: int
    target_output: int
    runtime_today: int
    fuel_usage_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.VARIABLE_HEATER

    @property
    def variable_heater_status(self) -> VariableHeaterStatus:
        """Get the heater status as enum."""
        try:
            return VariableHeaterStatus(self.status)
        except ValueError:
            return VariableHeaterStatus.OFF

    @property
    def is_running(self) -> bool:
        """Check if heater is currently running."""
        return self.status == VariableHeaterStatus.RUNNING

    @property
    def is_at_maximum(self) -> bool:
        """Check if heater is at maximum output."""
        return self.current_output >= 95


class VariableHeaterParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for variable heater parameters.

    Variable heater parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - On temp offset (2 bytes, int16)
    - Off temp offset (2 bytes, int16)
    - Min fire rate (1 byte, %)
    - Max fire rate (1 byte, %)
    - Degrees per percent (1 byte, tenths degree)
    - Reserved (1 byte)
    - Min on time (2 bytes, seconds)
    - Min off time (2 bytes, seconds)
    - Mode (1 byte)
    - Reserved (1 byte)
    - BTU rating (4 bytes, uint32)
    - Control bits (2 bytes)
    - Interlock bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns VARIABLE_HEATER device type."""
        return DeviceType.VARIABLE_HEATER

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> VariableHeaterParameters:
        """Parse variable heater parameters from hex data."""
        name_index = reader.read_uint16()
        on_temp_offset = Temperature(raw_value=reader.read_int16())
        off_temp_offset = Temperature(raw_value=reader.read_int16())
        min_fire_rate = reader.read_byte()
        max_fire_rate = reader.read_byte()
        degrees_per_percent = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        min_on_time = reader.read_uint16()
        min_off_time = reader.read_uint16()
        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        btu_rating = reader.read_uint32()
        control_bits = reader.read_uint16()
        interlock_bits = reader.read_uint16()

        return VariableHeaterParameters(
            header=header,
            name_index=name_index,
            on_temp_offset=on_temp_offset,
            off_temp_offset=off_temp_offset,
            min_fire_rate=min_fire_rate,
            max_fire_rate=max_fire_rate,
            degrees_per_percent=degrees_per_percent,
            min_on_time=min_on_time,
            min_off_time=min_off_time,
            mode=mode,
            btu_rating=btu_rating,
            control_bits=control_bits,
            interlock_bits=interlock_bits,
            raw_data=raw_data,
        )


class VariableHeaterVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for variable heater variables.

    Variable heater variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current output (1 byte, %)
    - Target output (1 byte, %)
    - Runtime today (2 bytes, minutes)
    - Fuel usage today (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns VARIABLE_HEATER device type."""
        return DeviceType.VARIABLE_HEATER

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> VariableHeaterVariables:
        """Parse variable heater variables from hex data."""
        status = reader.read_uint16()
        current_output = reader.read_byte()
        target_output = reader.read_byte()
        runtime_today = reader.read_uint16()
        fuel_usage_today = reader.read_uint16()

        return VariableHeaterVariables(
            header=header,
            status=status,
            current_output=current_output,
            target_output=target_output,
            runtime_today=runtime_today,
            fuel_usage_today=fuel_usage_today,
            raw_data=raw_data,
        )
