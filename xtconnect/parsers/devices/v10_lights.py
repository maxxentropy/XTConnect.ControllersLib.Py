"""
V10 Lights device parsing strategy.

V10 Lights are dimming-capable lighting systems that support gradual
on/off transitions (sunrise/sunset simulation) and intensity control.
They're used for poultry and livestock lighting programs.

Device Type: 27 (V10_LIGHTS)
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


class V10LightsMode(IntEnum):
    """V10 Lights operating modes."""

    OFF = 0
    """Lights are disabled."""

    AUTO = 1
    """Automatic timer-based control with dimming."""

    ON = 2
    """Lights are always on at set intensity."""

    MANUAL = 3
    """Manual intensity control."""


class V10LightsStatus(IntEnum):
    """V10 Lights runtime status values."""

    OFF = 0
    """Lights are currently off."""

    ON = 1
    """Lights are on at target intensity."""

    RAMPING_UP = 2
    """Lights are ramping up (sunrise)."""

    RAMPING_DOWN = 3
    """Lights are ramping down (sunset)."""


@dataclass(frozen=True)
class V10LightsParameters:
    """
    V10 Lights device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        on_time: On time (minutes from midnight).
        off_time: Off time (minutes from midnight).
        on_intensity: Target on intensity (0-100%).
        off_intensity: Off/minimum intensity (0-100%).
        sunrise_duration: Sunrise ramp duration in minutes.
        sunset_duration: Sunset ramp duration in minutes.
        mode: Operating mode (off, auto, on, manual).
        control_bits: Control configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    on_time: int
    off_time: int
    on_intensity: int
    off_intensity: int
    sunrise_duration: int
    sunset_duration: int
    mode: int
    control_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.V10_LIGHTS

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def v10_lights_mode(self) -> V10LightsMode:
        """Get the lights mode as enum."""
        try:
            return V10LightsMode(self.mode)
        except ValueError:
            return V10LightsMode.OFF

    def format_time(self, minutes_from_midnight: int) -> str:
        """Format time value as HH:MM string."""
        if minutes_from_midnight < 0 or minutes_from_midnight >= 1440:
            return "--:--"
        hours = minutes_from_midnight // 60
        mins = minutes_from_midnight % 60
        return f"{hours:02d}:{mins:02d}"


@dataclass(frozen=True)
class V10LightsVariables:
    """
    V10 Lights device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        current_intensity: Current light intensity (0-100%).
        target_intensity: Target light intensity (0-100%).
        runtime_today: Total runtime today in minutes.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    current_intensity: int
    target_intensity: int
    runtime_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.V10_LIGHTS

    @property
    def v10_lights_status(self) -> V10LightsStatus:
        """Get the lights status as enum."""
        try:
            return V10LightsStatus(self.status)
        except ValueError:
            return V10LightsStatus.OFF

    @property
    def is_on(self) -> bool:
        """Check if lights are currently on (any intensity)."""
        return self.current_intensity > 0

    @property
    def is_ramping(self) -> bool:
        """Check if lights are in a ramp transition."""
        return self.status in (V10LightsStatus.RAMPING_UP, V10LightsStatus.RAMPING_DOWN)


class V10LightsParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for V10 Lights parameters.

    V10 Lights parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - On time (2 bytes, minutes from midnight)
    - Off time (2 bytes, minutes from midnight)
    - On intensity (1 byte, %)
    - Off intensity (1 byte, %)
    - Sunrise duration (2 bytes, minutes)
    - Sunset duration (2 bytes, minutes)
    - Mode (1 byte)
    - Reserved (1 byte)
    - Control bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns V10_LIGHTS device type."""
        return DeviceType.V10_LIGHTS

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> V10LightsParameters:
        """Parse V10 Lights parameters from hex data."""
        name_index = reader.read_uint16()
        on_time = reader.read_uint16()
        off_time = reader.read_uint16()
        on_intensity = reader.read_byte()
        off_intensity = reader.read_byte()
        sunrise_duration = reader.read_uint16()
        sunset_duration = reader.read_uint16()
        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        control_bits = reader.read_uint16()

        return V10LightsParameters(
            header=header,
            name_index=name_index,
            on_time=on_time,
            off_time=off_time,
            on_intensity=on_intensity,
            off_intensity=off_intensity,
            sunrise_duration=sunrise_duration,
            sunset_duration=sunset_duration,
            mode=mode,
            control_bits=control_bits,
            raw_data=raw_data,
        )


class V10LightsVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for V10 Lights variables.

    V10 Lights variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Current intensity (1 byte, %)
    - Target intensity (1 byte, %)
    - Runtime today (2 bytes, minutes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns V10_LIGHTS device type."""
        return DeviceType.V10_LIGHTS

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> V10LightsVariables:
        """Parse V10 Lights variables from hex data."""
        status = reader.read_uint16()
        current_intensity = reader.read_byte()
        target_intensity = reader.read_byte()
        runtime_today = reader.read_uint16()

        return V10LightsVariables(
            header=header,
            status=status,
            current_intensity=current_intensity,
            target_intensity=target_intensity,
            runtime_today=runtime_today,
            raw_data=raw_data,
        )
