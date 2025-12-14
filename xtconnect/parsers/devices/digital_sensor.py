"""
Digital sensor device parsing strategy.

Digital sensors are generic digital input devices that read binary
on/off states. They can be used for door switches, motion detectors,
water flow sensors, and other binary inputs.

Device Type: 13 (DIGITAL_SENSOR)
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


class DigitalSensorType(IntEnum):
    """Digital sensor type codes."""

    GENERIC = 0
    """Generic digital input."""

    DOOR_SWITCH = 1
    """Door/gate position switch."""

    MOTION = 2
    """Motion detector."""

    FLOW = 3
    """Flow switch."""

    LEVEL = 4
    """Level switch."""


class DigitalInputState(IntEnum):
    """Digital input state values."""

    OFF = 0
    """Input is off/open/low."""

    ON = 1
    """Input is on/closed/high."""


@dataclass(frozen=True)
class DigitalSensorParameters:
    """
    Digital sensor device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        sensor_type: Type of digital sensor.
        invert_logic: Whether to invert input logic.
        alarm_on_active: Generate alarm when input is active.
        alarm_delay: Delay before alarm in seconds.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    sensor_type: int
    invert_logic: bool
    alarm_on_active: bool
    alarm_delay: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.DIGITAL_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def digital_sensor_type(self) -> DigitalSensorType:
        """Get the sensor type as enum."""
        try:
            return DigitalSensorType(self.sensor_type)
        except ValueError:
            return DigitalSensorType.GENERIC


@dataclass(frozen=True)
class DigitalSensorVariables:
    """
    Digital sensor device variables (runtime data).

    Attributes:
        header: Common device record header.
        current_state: Current input state (0=off, 1=on).
        on_count_today: Count of on transitions today.
        total_on_time: Total on time today in seconds.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    current_state: int
    on_count_today: int
    total_on_time: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.DIGITAL_SENSOR

    @property
    def input_state(self) -> DigitalInputState:
        """Get the input state as enum."""
        return DigitalInputState.ON if self.current_state else DigitalInputState.OFF

    @property
    def is_on(self) -> bool:
        """Check if input is currently on."""
        return self.current_state == 1

    @property
    def is_off(self) -> bool:
        """Check if input is currently off."""
        return self.current_state == 0


class DigitalSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for digital sensor parameters.

    Digital sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Sensor type (1 byte)
    - Flags (1 byte) - bit 0: invert, bit 1: alarm on active
    - Alarm delay (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns DIGITAL_SENSOR device type."""
        return DeviceType.DIGITAL_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> DigitalSensorParameters:
        """Parse digital sensor parameters from hex data."""
        name_index = reader.read_uint16()
        sensor_type = reader.read_byte()
        flags = reader.read_byte()
        alarm_delay = reader.read_uint16()

        return DigitalSensorParameters(
            header=header,
            name_index=name_index,
            sensor_type=sensor_type,
            invert_logic=bool(flags & 0x01),
            alarm_on_active=bool(flags & 0x02),
            alarm_delay=alarm_delay,
            raw_data=raw_data,
        )


class DigitalSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for digital sensor variables.

    Digital sensor variable record structure (after 8-byte header):
    - Current state (1 byte)
    - Reserved (1 byte)
    - On count today (2 bytes)
    - Total on time (2 bytes, seconds)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns DIGITAL_SENSOR device type."""
        return DeviceType.DIGITAL_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> DigitalSensorVariables:
        """Parse digital sensor variables from hex data."""
        current_state = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        on_count_today = reader.read_uint16()
        total_on_time = reader.read_uint16()

        return DigitalSensorVariables(
            header=header,
            current_state=current_state,
            on_count_today=on_count_today,
            total_on_time=total_on_time,
            raw_data=raw_data,
        )
