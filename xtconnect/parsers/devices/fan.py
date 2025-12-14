"""
Fan device parsing strategy.

Fans are one of the most common devices in agricultural ventilation.
They can be staged, have temperature-based activation, and support
various control modes.

Device Type: 8 (FAN)
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


class FanMode(IntEnum):
    """Fan operating modes."""

    OFF = 0
    """Fan is disabled."""

    AUTO = 1
    """Automatic temperature-based control."""

    ON = 2
    """Fan is always on."""

    TIMER = 3
    """Timer-based cycling."""

    MINIMUM = 4
    """Minimum ventilation mode."""


class FanStatus(IntEnum):
    """Fan runtime status values."""

    OFF = 0
    """Fan is currently off."""

    RUNNING = 1
    """Fan is currently running."""

    STAGING_DELAY = 2
    """Fan is in staging delay period."""

    INHIBITED = 3
    """Fan is inhibited by temperature or interlock."""


@dataclass(frozen=True)
class FanParameters:
    """
    Fan device parameters.

    Contains configuration for fan operation including staging,
    temperature offsets, and timing parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        stage_number: Staging order (1-based, fans start in order).
        on_temp_offset: Temperature offset to turn on (tenths of degree).
        off_temp_offset: Temperature offset to turn off (tenths of degree).
        min_on_time: Minimum on time in seconds.
        min_off_time: Minimum off time in seconds.
        staging_delay: Delay between stage activations in seconds.
        mode: Operating mode (auto, on, off, timer, minimum).
        cfm_rating: Airflow rating in CFM (Cubic Feet per Minute).
        control_bits: Control configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    stage_number: int
    on_temp_offset: Temperature
    off_temp_offset: Temperature
    min_on_time: int
    min_off_time: int
    staging_delay: int
    mode: int
    cfm_rating: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.FAN

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def fan_mode(self) -> FanMode:
        """Get the fan mode as enum."""
        try:
            return FanMode(self.mode)
        except ValueError:
            return FanMode.OFF

    @property
    def is_auto_mode(self) -> bool:
        """Check if fan is in automatic mode."""
        return self.mode == FanMode.AUTO

    @property
    def is_minimum_vent(self) -> bool:
        """Check if fan is used for minimum ventilation."""
        return self.mode == FanMode.MINIMUM


@dataclass(frozen=True)
class FanVariables:
    """
    Fan device variables (runtime data).

    Contains the current operating state and runtime counters.

    Attributes:
        header: Common device record header.
        status: Current operating status.
        runtime_today: Total runtime today in minutes.
        runtime_total: Total runtime in hours (lifetime).
        cycles_today: Number of on/off cycles today.
        current_stage: Current stage position (0 = off).
        remaining_delay: Remaining staging delay in seconds.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    runtime_today: int
    runtime_total: int
    cycles_today: int
    current_stage: int
    remaining_delay: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.FAN

    @property
    def fan_status(self) -> FanStatus:
        """Get the fan status as enum."""
        try:
            return FanStatus(self.status)
        except ValueError:
            return FanStatus.OFF

    @property
    def is_running(self) -> bool:
        """Check if fan is currently running."""
        return self.status == FanStatus.RUNNING

    @property
    def is_off(self) -> bool:
        """Check if fan is currently off."""
        return self.status == FanStatus.OFF


class FanParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for fan parameters.

    Fan parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Stage number (1 byte)
    - Reserved (1 byte)
    - On temp offset (2 bytes, int16)
    - Off temp offset (2 bytes, int16)
    - Min on time (2 bytes)
    - Min off time (2 bytes)
    - Staging delay (2 bytes)
    - Mode (1 byte)
    - Reserved (1 byte)
    - CFM rating (2 bytes)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns FAN device type."""
        return DeviceType.FAN

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> FanParameters:
        """
        Parse fan parameters from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed FanParameters.
        """
        name_index = reader.read_uint16()
        stage_number = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        on_temp_offset = Temperature(raw_value=reader.read_int16())
        off_temp_offset = Temperature(raw_value=reader.read_int16())

        min_on_time = reader.read_uint16()
        min_off_time = reader.read_uint16()
        staging_delay = reader.read_uint16()

        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        cfm_rating = reader.read_uint16()
        control_bits = reader.read_uint16()

        return FanParameters(
            header=header,
            name_index=name_index,
            stage_number=stage_number,
            on_temp_offset=on_temp_offset,
            off_temp_offset=off_temp_offset,
            min_on_time=min_on_time,
            min_off_time=min_off_time,
            staging_delay=staging_delay,
            mode=mode,
            cfm_rating=cfm_rating,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class FanVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for fan variables.

    Fan variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Runtime today (2 bytes, minutes)
    - Runtime total (2 bytes, hours)
    - Cycles today (2 bytes)
    - Current stage (1 byte)
    - Reserved (1 byte)
    - Remaining delay (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns FAN device type."""
        return DeviceType.FAN

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> FanVariables:
        """
        Parse fan variables from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed FanVariables.
        """
        status = reader.read_uint16()
        runtime_today = reader.read_uint16()
        runtime_total = reader.read_uint16()
        cycles_today = reader.read_uint16()

        current_stage = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        remaining_delay = reader.read_uint16()

        return FanVariables(
            header=header,
            status=status,
            runtime_today=runtime_today,
            runtime_total=runtime_total,
            cycles_today=cycles_today,
            current_stage=current_stage,
            remaining_delay=remaining_delay,
            raw_data=raw_data,
        )
