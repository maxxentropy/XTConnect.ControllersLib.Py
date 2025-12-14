"""
Feed sensor device parsing strategy.

Feed sensors monitor feed bin levels and consumption. They can use
various technologies including ultrasonic level sensors, load cells,
or flow meters.

Device Type: 10 (FEED_SENSOR)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xtconnect.models.records import DeviceRecordHeader, DeviceType
from xtconnect.parsers.device_registry import (
    DeviceParameterStrategy,
    DeviceVariableStrategy,
)

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader


@dataclass(frozen=True)
class FeedSensorParameters:
    """
    Feed sensor device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        bin_capacity: Bin capacity in pounds.
        low_level_alarm: Low level alarm threshold (%).
        sensor_type: Sensor hardware type identifier.
        calibration_factor: Calibration factor for sensor readings.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    bin_capacity: int
    low_level_alarm: int
    sensor_type: int
    calibration_factor: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.FEED_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number


@dataclass(frozen=True)
class FeedSensorVariables:
    """
    Feed sensor device variables (runtime data).

    Attributes:
        header: Common device record header.
        current_level: Current level (%).
        consumption_today: Feed consumed today in pounds.
        consumption_total: Total feed consumed in pounds.
        sensor_status: Sensor status flags (0 = OK).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    current_level: int
    consumption_today: int
    consumption_total: int
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.FEED_SENSOR

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return self.sensor_status == 0

    @property
    def is_low(self) -> bool:
        """Check if feed level is critically low (< 10%)."""
        return self.current_level < 10


class FeedSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for feed sensor parameters.

    Feed sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Bin capacity (4 bytes, uint32, pounds)
    - Low level alarm (1 byte, %)
    - Sensor type (1 byte)
    - Calibration factor (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns FEED_SENSOR device type."""
        return DeviceType.FEED_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> FeedSensorParameters:
        """Parse feed sensor parameters from hex data."""
        name_index = reader.read_uint16()
        bin_capacity = reader.read_uint32()
        low_level_alarm = reader.read_byte()
        sensor_type = reader.read_byte()
        calibration_factor = reader.read_uint16()

        return FeedSensorParameters(
            header=header,
            name_index=name_index,
            bin_capacity=bin_capacity,
            low_level_alarm=low_level_alarm,
            sensor_type=sensor_type,
            calibration_factor=calibration_factor,
            raw_data=raw_data,
        )


class FeedSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for feed sensor variables.

    Feed sensor variable record structure (after 8-byte header):
    - Current level (1 byte, %)
    - Reserved (1 byte)
    - Consumption today (4 bytes, uint32, pounds)
    - Consumption total (4 bytes, uint32, pounds)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns FEED_SENSOR device type."""
        return DeviceType.FEED_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> FeedSensorVariables:
        """Parse feed sensor variables from hex data."""
        current_level = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        consumption_today = reader.read_uint32()
        consumption_total = reader.read_uint32()
        sensor_status = reader.read_uint16()

        return FeedSensorVariables(
            header=header,
            current_level=current_level,
            consumption_today=consumption_today,
            consumption_total=consumption_total,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
