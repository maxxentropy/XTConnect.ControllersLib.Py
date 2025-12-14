"""
Water sensor device parsing strategy.

Water sensors monitor water consumption, typically using flow meters.
They track daily and total consumption and can detect abnormal
usage patterns.

Device Type: 11 (WATER_SENSOR)
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
class WaterSensorParameters:
    """
    Water sensor device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        pulses_per_gallon: Calibration: flow meter pulses per gallon.
        high_flow_alarm: High flow rate alarm threshold (gallons/hour).
        no_flow_alarm_time: No flow alarm delay in minutes.
        sensor_type: Sensor hardware type identifier.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    pulses_per_gallon: int
    high_flow_alarm: int
    no_flow_alarm_time: int
    sensor_type: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.WATER_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number


@dataclass(frozen=True)
class WaterSensorVariables:
    """
    Water sensor device variables (runtime data).

    Attributes:
        header: Common device record header.
        flow_rate: Current flow rate (gallons/hour).
        consumption_today: Water consumed today in gallons.
        consumption_total: Total water consumed in gallons.
        sensor_status: Sensor status flags (0 = OK).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    flow_rate: int
    consumption_today: int
    consumption_total: int
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.WATER_SENSOR

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return self.sensor_status == 0

    @property
    def has_flow(self) -> bool:
        """Check if water is currently flowing."""
        return self.flow_rate > 0


class WaterSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for water sensor parameters.

    Water sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Pulses per gallon (2 bytes)
    - High flow alarm (2 bytes, gallons/hour)
    - No flow alarm time (2 bytes, minutes)
    - Sensor type (1 byte)
    - Reserved (1 byte)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns WATER_SENSOR device type."""
        return DeviceType.WATER_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> WaterSensorParameters:
        """Parse water sensor parameters from hex data."""
        name_index = reader.read_uint16()
        pulses_per_gallon = reader.read_uint16()
        high_flow_alarm = reader.read_uint16()
        no_flow_alarm_time = reader.read_uint16()
        sensor_type = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        return WaterSensorParameters(
            header=header,
            name_index=name_index,
            pulses_per_gallon=pulses_per_gallon,
            high_flow_alarm=high_flow_alarm,
            no_flow_alarm_time=no_flow_alarm_time,
            sensor_type=sensor_type,
            raw_data=raw_data,
        )


class WaterSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for water sensor variables.

    Water sensor variable record structure (after 8-byte header):
    - Flow rate (2 bytes, gallons/hour)
    - Consumption today (4 bytes, uint32, gallons)
    - Consumption total (4 bytes, uint32, gallons)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns WATER_SENSOR device type."""
        return DeviceType.WATER_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> WaterSensorVariables:
        """Parse water sensor variables from hex data."""
        flow_rate = reader.read_uint16()
        consumption_today = reader.read_uint32()
        consumption_total = reader.read_uint32()
        sensor_status = reader.read_uint16()

        return WaterSensorVariables(
            header=header,
            flow_rate=flow_rate,
            consumption_today=consumption_today,
            consumption_total=consumption_total,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
