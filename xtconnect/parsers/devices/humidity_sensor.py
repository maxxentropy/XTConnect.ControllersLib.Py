"""
Humidity sensor device parsing strategy.

Humidity sensors measure both temperature and humidity. They combine the
functionality of air sensors with humidity measurement capabilities.

Device Type: 2 (HUMIDITY_SENSOR)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from xtconnect.models.records import DeviceRecordHeader, DeviceType, Humidity, Temperature
from xtconnect.parsers.device_registry import (
    DeviceParameterStrategy,
    DeviceVariableStrategy,
)

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader


@dataclass(frozen=True)
class HumiditySensorParameters:
    """
    Humidity sensor device parameters.

    Humidity sensors have calibration offsets for both temperature and
    humidity measurements.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        temp_calibration_offset: Temperature calibration offset.
        humidity_calibration_offset: Humidity calibration offset (0-100%).
        sensor_type: Sensor hardware type identifier.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    temp_calibration_offset: Temperature
    humidity_calibration_offset: int
    sensor_type: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.HUMIDITY_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number


@dataclass(frozen=True)
class HumiditySensorVariables:
    """
    Humidity sensor device variables (runtime data).

    Contains the current temperature and humidity readings.

    Attributes:
        header: Common device record header.
        current_temperature: Current temperature reading.
        current_humidity: Current humidity reading (0-100%).
        sensor_status: Sensor status flags (0 = OK).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    current_temperature: Temperature
    current_humidity: Humidity
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.HUMIDITY_SENSOR

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return (
            self.sensor_status == 0
            and self.current_temperature.is_valid
            and self.current_humidity.is_valid
        )

    @property
    def has_error(self) -> bool:
        """Check if sensor has an error condition."""
        return (
            self.sensor_status != 0
            or self.current_temperature.is_nan
            or not self.current_humidity.is_valid
        )


class HumiditySensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for humidity sensor parameters.

    Humidity sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Temp calibration offset (2 bytes, int16)
    - Humidity calibration offset (1 byte, %)
    - Sensor type (1 byte)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns HUMIDITY_SENSOR device type."""
        return DeviceType.HUMIDITY_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> HumiditySensorParameters:
        """
        Parse humidity sensor parameters from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed HumiditySensorParameters.
        """
        name_index = reader.read_uint16()
        temp_calibration_offset = Temperature(raw_value=reader.read_int16())
        humidity_calibration_offset = reader.read_byte()
        sensor_type = reader.read_byte()

        return HumiditySensorParameters(
            header=header,
            name_index=name_index,
            temp_calibration_offset=temp_calibration_offset,
            humidity_calibration_offset=humidity_calibration_offset,
            sensor_type=sensor_type,
            raw_data=raw_data,
        )


class HumiditySensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for humidity sensor variables.

    Humidity sensor variable record structure (after 8-byte header):
    - Current temperature (2 bytes, int16)
    - Current humidity (1 byte, %)
    - Reserved (1 byte)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns HUMIDITY_SENSOR device type."""
        return DeviceType.HUMIDITY_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> HumiditySensorVariables:
        """
        Parse humidity sensor variables from hex data.

        Args:
            reader: HexStringReader positioned after the header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Parsed HumiditySensorVariables.
        """
        current_temperature = Temperature(raw_value=reader.read_int16())
        current_humidity = Humidity(value=reader.read_byte())
        reader.skip_bytes(1)  # Reserved
        sensor_status = reader.read_uint16()

        return HumiditySensorVariables(
            header=header,
            current_temperature=current_temperature,
            current_humidity=current_humidity,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
