"""
Air sensor device parsing strategy.

Air sensors are the simplest device type - they measure temperature
and optionally humidity. They have minimal configuration parameters.

Device Type: 1 (AIR_SENSOR)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xtconnect.models.records import DeviceRecordHeader, DeviceType, Temperature
from xtconnect.parsers.device_registry import (
    DeviceParameterStrategy,
    DeviceVariableStrategy,
)

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader


@dataclass(frozen=True)
class AirSensorParameters:
    """
    Air sensor device parameters.

    Air sensors have minimal configuration - primarily just
    identification and calibration offset.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        calibration_offset: Temperature calibration offset (tenths of degree).
        sensor_type: Sensor hardware type identifier.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    calibration_offset: Temperature
    sensor_type: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.AIR_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def module_address(self) -> int:
        """Get the module address from header."""
        return self.header.module_address

    @property
    def channel_number(self) -> int:
        """Get the channel number from header."""
        return self.header.channel_number


@dataclass(frozen=True)
class AirSensorVariables:
    """
    Air sensor device variables (runtime data).

    Contains the current temperature reading and sensor status.

    Attributes:
        header: Common device record header.
        current_temperature: Current temperature reading.
        sensor_status: Sensor status flags (0 = OK, non-zero = error).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    current_temperature: Temperature
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.AIR_SENSOR

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return self.sensor_status == 0 and self.current_temperature.is_valid

    @property
    def has_error(self) -> bool:
        """Check if sensor has an error condition."""
        return self.sensor_status != 0 or self.current_temperature.is_nan


class AirSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for air sensor parameters.

    Air sensor parameter records are simple:
    - Header (8 bytes) - already parsed
    - Name index (2 bytes)
    - Calibration offset (2 bytes, int16)
    - Sensor type (1 byte)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns AIR_SENSOR device type."""
        return DeviceType.AIR_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> AirSensorParameters:
        """
        Parse air sensor parameters from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed AirSensorParameters.
        """
        # Read device-specific fields
        name_index = reader.read_uint16()
        calibration_offset = Temperature(raw_value=reader.read_int16())
        sensor_type = reader.read_byte()

        return AirSensorParameters(
            header=header,
            name_index=name_index,
            calibration_offset=calibration_offset,
            sensor_type=sensor_type,
            raw_data=raw_data,
        )


class AirSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for air sensor variables.

    Air sensor variable records contain:
    - Header (8 bytes) - already parsed
    - Current temperature (2 bytes, int16)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns AIR_SENSOR device type."""
        return DeviceType.AIR_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> AirSensorVariables:
        """
        Parse air sensor variables from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed AirSensorVariables.
        """
        current_temperature = Temperature(raw_value=reader.read_int16())
        sensor_status = reader.read_uint16()

        return AirSensorVariables(
            header=header,
            current_temperature=current_temperature,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
