"""
Static pressure sensor device parsing strategy.

Static sensors measure building static pressure, typically used for
inlet position control and ventilation monitoring. Pressure is measured
in hundredths of an inch of water column (WC).

Device Type: 12 (STATIC_SENSOR)
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
class StaticSensorParameters:
    """
    Static pressure sensor device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        calibration_offset: Pressure calibration offset (hundredths inch WC).
        high_alarm_setpoint: High pressure alarm setpoint.
        low_alarm_setpoint: Low pressure alarm setpoint.
        sensor_type: Sensor hardware type identifier.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    calibration_offset: int
    high_alarm_setpoint: int
    low_alarm_setpoint: int
    sensor_type: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.STATIC_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def calibration_inches_wc(self) -> float:
        """Get calibration offset in inches WC."""
        return self.calibration_offset / 100.0


@dataclass(frozen=True)
class StaticSensorVariables:
    """
    Static pressure sensor device variables (runtime data).

    Attributes:
        header: Common device record header.
        current_reading: Current pressure reading (hundredths inch WC).
        sensor_status: Sensor status flags (0 = OK).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    current_reading: int
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.STATIC_SENSOR

    @property
    def reading_inches_wc(self) -> float:
        """Get current reading in inches WC."""
        return self.current_reading / 100.0

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return self.sensor_status == 0


class StaticSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for static sensor parameters.

    Static sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Calibration offset (2 bytes, int16, hundredths inch WC)
    - High alarm setpoint (2 bytes)
    - Low alarm setpoint (2 bytes)
    - Sensor type (1 byte)
    - Reserved (1 byte)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns STATIC_SENSOR device type."""
        return DeviceType.STATIC_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> StaticSensorParameters:
        """Parse static sensor parameters from hex data."""
        name_index = reader.read_uint16()
        calibration_offset = reader.read_int16()
        high_alarm_setpoint = reader.read_uint16()
        low_alarm_setpoint = reader.read_uint16()
        sensor_type = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        return StaticSensorParameters(
            header=header,
            name_index=name_index,
            calibration_offset=calibration_offset,
            high_alarm_setpoint=high_alarm_setpoint,
            low_alarm_setpoint=low_alarm_setpoint,
            sensor_type=sensor_type,
            raw_data=raw_data,
        )


class StaticSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for static sensor variables.

    Static sensor variable record structure (after 8-byte header):
    - Current reading (2 bytes, int16, hundredths inch WC)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns STATIC_SENSOR device type."""
        return DeviceType.STATIC_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> StaticSensorVariables:
        """Parse static sensor variables from hex data."""
        current_reading = reader.read_int16()
        sensor_status = reader.read_uint16()

        return StaticSensorVariables(
            header=header,
            current_reading=current_reading,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
