"""
Gas sensor device parsing strategy.

Gas sensors measure air quality gases like ammonia (NH3) and carbon
dioxide (CO2). They're critical for animal welfare and ventilation
control in agricultural environments.

Device Type: 28 (GAS_SENSOR)
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


class GasType(IntEnum):
    """Types of gases that can be measured."""

    UNKNOWN = 0
    """Unknown gas type."""

    AMMONIA = 1
    """Ammonia (NH3) - measured in PPM."""

    CARBON_DIOXIDE = 2
    """Carbon dioxide (CO2) - measured in PPM."""

    HYDROGEN_SULFIDE = 3
    """Hydrogen sulfide (H2S) - measured in PPM."""


@dataclass(frozen=True)
class GasSensorParameters:
    """
    Gas sensor device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        gas_type: Type of gas being measured.
        high_alarm_level: High level alarm threshold (PPM).
        ventilation_trigger: Level to increase ventilation (PPM).
        calibration_offset: Calibration offset (PPM).
        sensor_type: Sensor hardware type identifier.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    gas_type: int
    high_alarm_level: int
    ventilation_trigger: int
    calibration_offset: int
    sensor_type: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.GAS_SENSOR

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def measured_gas(self) -> GasType:
        """Get the gas type as enum."""
        try:
            return GasType(self.gas_type)
        except ValueError:
            return GasType.UNKNOWN


@dataclass(frozen=True)
class GasSensorVariables:
    """
    Gas sensor device variables (runtime data).

    Attributes:
        header: Common device record header.
        current_level: Current gas level (PPM).
        peak_level_today: Peak level recorded today (PPM).
        sensor_status: Sensor status flags (0 = OK).
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    current_level: int
    peak_level_today: int
    sensor_status: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.GAS_SENSOR

    @property
    def is_ok(self) -> bool:
        """Check if sensor is operating normally."""
        return self.sensor_status == 0


class GasSensorParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for gas sensor parameters.

    Gas sensor parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Gas type (1 byte)
    - Reserved (1 byte)
    - High alarm level (2 bytes, PPM)
    - Ventilation trigger (2 bytes, PPM)
    - Calibration offset (2 bytes, int16, PPM)
    - Sensor type (1 byte)
    - Reserved (1 byte)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns GAS_SENSOR device type."""
        return DeviceType.GAS_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> GasSensorParameters:
        """Parse gas sensor parameters from hex data."""
        name_index = reader.read_uint16()
        gas_type = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        high_alarm_level = reader.read_uint16()
        ventilation_trigger = reader.read_uint16()
        calibration_offset = reader.read_int16()
        sensor_type = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        return GasSensorParameters(
            header=header,
            name_index=name_index,
            gas_type=gas_type,
            high_alarm_level=high_alarm_level,
            ventilation_trigger=ventilation_trigger,
            calibration_offset=calibration_offset,
            sensor_type=sensor_type,
            raw_data=raw_data,
        )


class GasSensorVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for gas sensor variables.

    Gas sensor variable record structure (after 8-byte header):
    - Current level (2 bytes, PPM)
    - Peak level today (2 bytes, PPM)
    - Sensor status (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns GAS_SENSOR device type."""
        return DeviceType.GAS_SENSOR

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> GasSensorVariables:
        """Parse gas sensor variables from hex data."""
        current_level = reader.read_uint16()
        peak_level_today = reader.read_uint16()
        sensor_status = reader.read_uint16()

        return GasSensorVariables(
            header=header,
            current_level=current_level,
            peak_level_today=peak_level_today,
            sensor_status=sensor_status,
            raw_data=raw_data,
        )
