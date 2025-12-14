"""
Position sensor device parsing strategy.

Position sensors provide feedback on the actual position of mechanical
devices like inlets, curtains, and vents. They can use various sensing
technologies (potentiometer, encoder, limit switches).

Device Type: 14 (POSITION_SENSOR)
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
class PositionSensorParameters:
    """
    Position sensor device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        min_raw_value: Raw value at 0% position.
        max_raw_value: Raw value at 100% position.
        linked_device: Device index this sensor provides feedback for.
        sensor_type: Sensor hardware type identifier.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    min_raw_value: int
    max_raw_value: int
    linked_device: int
    sensor_type: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.POSITION_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def range(self) -> int:
        """Get the raw value range."""
        return abs(self.max_raw_value - self.min_raw_value)


@dataclass(frozen=True)
class PositionSensorVariables:
    """
    Position sensor device variables (runtime data).

    Attributes:
        header: Common device record header.
        raw_value: Raw sensor reading.
        calculated_position: Calculated position (0-100%).
        sensor_status: Sensor status flags (0 = OK).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    raw_value: int
    calculated_position: int
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.POSITION_SENSOR

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return self.sensor_status == 0

    @property
    def is_fully_open(self) -> bool:
        """Check if position is fully open (>= 95%)."""
        return self.calculated_position >= 95

    @property
    def is_fully_closed(self) -> bool:
        """Check if position is fully closed (<= 5%)."""
        return self.calculated_position <= 5


class PositionSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for position sensor parameters.

    Position sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Min raw value (2 bytes)
    - Max raw value (2 bytes)
    - Linked device (2 bytes)
    - Sensor type (1 byte)
    - Reserved (1 byte)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns POSITION_SENSOR device type."""
        return DeviceType.POSITION_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> PositionSensorParameters:
        """Parse position sensor parameters from hex data."""
        name_index = reader.read_uint16()
        min_raw_value = reader.read_uint16()
        max_raw_value = reader.read_uint16()
        linked_device = reader.read_uint16()
        sensor_type = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        return PositionSensorParameters(
            header=header,
            name_index=name_index,
            min_raw_value=min_raw_value,
            max_raw_value=max_raw_value,
            linked_device=linked_device,
            sensor_type=sensor_type,
            raw_data=raw_data,
        )


class PositionSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for position sensor variables.

    Position sensor variable record structure (after 8-byte header):
    - Raw value (2 bytes)
    - Calculated position (1 byte, %)
    - Reserved (1 byte)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns POSITION_SENSOR device type."""
        return DeviceType.POSITION_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> PositionSensorVariables:
        """Parse position sensor variables from hex data."""
        raw_value = reader.read_uint16()
        calculated_position = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        sensor_status = reader.read_uint16()

        return PositionSensorVariables(
            header=header,
            raw_value=raw_value,
            calculated_position=calculated_position,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
