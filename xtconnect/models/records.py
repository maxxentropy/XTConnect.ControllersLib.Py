"""
Pydantic models for PCMI protocol records.

This module defines the core data structures used throughout the library,
implemented as immutable Pydantic models with validation.

Design principles:
- All models are frozen (immutable) by default
- Value objects use custom validation to match protocol constraints
- Records mirror the structure of the .NET library for familiarity
- NaN/invalid values are represented explicitly, not as None
"""

from __future__ import annotations

from enum import IntEnum
from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from xtconnect.protocol.constants import ProtocolConstants


class TemperatureUnit(IntEnum):
    """Temperature display units."""

    FAHRENHEIT = 0
    CELSIUS = 1


class Temperature(BaseModel):
    """
    Temperature value with 0.1-degree precision.

    Temperature is stored internally as a signed 16-bit integer representing
    tenths of a degree Fahrenheit. This matches the wire format used by
    Valco controllers.

    Special value 0x7FFF (32767) represents NaN (sensor error/not available).
    Valid range: -32.7°F to 327.6°F (-36.2°C to 164.2°C)

    Example:
        >>> temp = Temperature(raw_value=725)  # 72.5°F
        >>> temp.fahrenheit
        72.5
        >>> temp.celsius
        22.5

        >>> nan_temp = Temperature.nan()
        >>> nan_temp.is_nan
        True
    """

    model_config = ConfigDict(frozen=True)

    raw_value: int = Field(ge=-32768, le=32767, description="Raw value in tenths of degree F")

    # Constants
    NAN_VALUE: Final[int] = 0x7FFF
    """Special value representing Not-a-Number (sensor error)."""

    @property
    def is_nan(self) -> bool:
        """Check if this temperature represents NaN (sensor error)."""
        return self.raw_value == self.NAN_VALUE

    @property
    def is_valid(self) -> bool:
        """Check if this temperature is a valid measurement."""
        return not self.is_nan

    @property
    def fahrenheit(self) -> float | None:
        """
        Get temperature in degrees Fahrenheit.

        Returns:
            Temperature in °F, or None if NaN.
        """
        if self.is_nan:
            return None
        return self.raw_value / 10.0

    @property
    def celsius(self) -> float | None:
        """
        Get temperature in degrees Celsius.

        Returns:
            Temperature in °C, or None if NaN.
        """
        f = self.fahrenheit
        if f is None:
            return None
        return (f - 32.0) * 5.0 / 9.0

    def format(self, unit: TemperatureUnit = TemperatureUnit.FAHRENHEIT) -> str:
        """
        Format temperature as a string with units.

        Args:
            unit: Temperature unit for display.

        Returns:
            Formatted temperature string.
        """
        if self.is_nan:
            return "NaN"

        if unit == TemperatureUnit.CELSIUS:
            return f"{self.celsius:.1f}°C"
        return f"{self.fahrenheit:.1f}°F"

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        if self.is_nan:
            return "Temperature(NaN)"
        return f"Temperature({self.fahrenheit:.1f}°F)"

    @classmethod
    def nan(cls) -> Temperature:
        """Create a NaN temperature value."""
        return cls(raw_value=cls.NAN_VALUE)

    @classmethod
    def from_fahrenheit(cls, value: float) -> Temperature:
        """
        Create a temperature from a Fahrenheit value.

        Args:
            value: Temperature in degrees Fahrenheit.

        Returns:
            Temperature instance.

        Raises:
            ValueError: If value would conflict with NaN representation.
        """
        raw = int(round(value * 10))

        if raw == cls.NAN_VALUE:
            raise ValueError(
                f"Temperature {value}°F would conflict with NaN representation (3276.7°F)"
            )

        return cls(raw_value=raw)

    @classmethod
    def from_celsius(cls, value: float) -> Temperature:
        """
        Create a temperature from a Celsius value.

        Args:
            value: Temperature in degrees Celsius.

        Returns:
            Temperature instance.
        """
        fahrenheit = (value * 9.0 / 5.0) + 32.0
        return cls.from_fahrenheit(fahrenheit)

    @classmethod
    def from_raw(cls, raw_value: int) -> Temperature:
        """
        Create a temperature from a raw wire format value.

        Args:
            raw_value: Raw value (tenths of degree Fahrenheit).

        Returns:
            Temperature instance.
        """
        return cls(raw_value=raw_value)


class SerialNumber(BaseModel):
    """
    Valco controller serial number.

    Serial numbers are exactly 8 ASCII digits (0-9).
    Example: "00009001"

    Example:
        >>> sn = SerialNumber(value="00009001")
        >>> str(sn)
        '00009001'
        >>> sn.as_int
        9001
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(
        min_length=8,
        max_length=8,
        pattern=r"^\d{8}$",
        description="8-digit serial number",
    )

    @field_validator("value")
    @classmethod
    def validate_digits(cls, v: str) -> str:
        """Ensure serial number contains only digits."""
        if not v.isdigit():
            raise ValueError("Serial number must contain only digits (0-9)")
        return v

    @property
    def as_int(self) -> int:
        """Get serial number as an integer for numeric comparison."""
        return int(self.value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"SerialNumber({self.value!r})"

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def parse(cls, value: str) -> SerialNumber:
        """
        Parse a serial number from a string.

        Args:
            value: Serial number string (will be stripped and validated).

        Returns:
            SerialNumber instance.

        Raises:
            ValueError: If value is not a valid serial number.
        """
        return cls(value=value.strip())


class Humidity(BaseModel):
    """
    Relative humidity percentage.

    Humidity values range from 0% to 100%.

    Example:
        >>> humidity = Humidity(value=65)
        >>> humidity.value
        65
    """

    model_config = ConfigDict(frozen=True)

    value: int = Field(ge=0, le=100, description="Humidity percentage (0-100)")

    def __str__(self) -> str:
        return f"{self.value}%"

    def __repr__(self) -> str:
        return f"Humidity({self.value}%)"


class DeviceType(IntEnum):
    """
    Device types supported by Valco PCMI controllers.

    Device type codes are defined in the controller firmware and used in
    device parameter and variable records to identify the device type.
    Values 17-24 are reserved/unused in current firmware.
    """

    UNKNOWN = 0
    """Unknown or invalid device type."""

    AIR_SENSOR = 1
    """Air temperature sensor."""

    HUMIDITY_SENSOR = 2
    """Humidity sensor."""

    INLET = 3
    """Inlet/vent control."""

    CURTAIN = 4
    """Side curtain control."""

    RIDGE_VENT = 5
    """Ridge vent control."""

    HEATER = 6
    """Heater control."""

    COOLPAD = 7
    """Evaporative cooling pad."""

    FAN = 8
    """Fan control."""

    TIMED = 9
    """Timed device - lights, feeders, etc."""

    FEED_SENSOR = 10
    """Feed level sensor."""

    WATER_SENSOR = 11
    """Water meter/sensor."""

    STATIC_SENSOR = 12
    """Static pressure sensor."""

    DIGITAL_SENSOR = 13
    """Generic digital sensor."""

    POSITION_SENSOR = 14
    """Position feedback sensor."""

    CHIMNEY = 15
    """Chimney/natural vent."""

    SWITCH = 16
    """Generic switch/relay."""

    # Values 17-24 are reserved/unused

    VARIABLE_HEATER = 25
    """Variable output heater."""

    VFD_FAN = 26
    """Variable frequency drive fan."""

    V10_LIGHTS = 27
    """V10 lighting control."""

    GAS_SENSOR = 28
    """Gas sensor - CO2, NH3, etc."""


class DeviceRecordHeader(BaseModel):
    """
    Common header for device parameter and variable records.

    This header appears at the beginning of all device records and
    identifies the device type, location, and format version.
    """

    model_config = ConfigDict(frozen=True)

    record_size_words: int = Field(ge=0, description="Record size in words")
    zone_number: int = Field(ge=1, le=9, description="Zone number (1-9)")
    record_type: int = Field(ge=0, le=255, description="Record type code")
    record_format: int = Field(ge=0, le=255, description="Record format version")
    device_type: DeviceType = Field(description="Device type")
    device_subtype: int = Field(ge=0, le=255, description="Device subtype")
    module_address: int = Field(ge=0, le=255, description="Module address on RS-485 bus")
    channel_number: int = Field(ge=0, le=255, description="Channel number on module")


class VersionRecord(BaseModel):
    """
    Controller version information record.

    Contains the firmware version string and date code.
    Returned in response to PCMI_SEND_VERSION command.
    """

    model_config = ConfigDict(frozen=True)

    version_string: str = Field(max_length=14, description="Firmware version string")
    date_code: str = Field(max_length=8, description="Firmware date code")
    raw_data: str | None = Field(default=None, description="Original hex data")

    def __str__(self) -> str:
        return f"{self.version_string} ({self.date_code})"


class ZoneParameters(BaseModel):
    """
    Zone parameter record containing all configuration for a zone.

    Zone parameters define the operational settings for a zone, including
    temperature setpoints, alarm thresholds, control parameters, and
    animal production information.

    This is an immutable record matching the structure from the controller.
    """

    model_config = ConfigDict(frozen=True)

    # Header
    record_size_words: int = Field(ge=0, description="Record size in words")
    zone_number: int = Field(ge=1, le=9, description="Zone number (1-9)")
    record_type: int = Field(ge=0, le=255, description="Record type code")
    record_format: int = Field(ge=0, le=255, description="Record format version")

    # Temperature settings
    temp_setpoint: Temperature = Field(description="Target temperature setpoint")
    high_temp_alarm_offset: Temperature = Field(description="High temp alarm offset from setpoint")
    low_temp_alarm_offset: Temperature = Field(description="Low temp alarm offset from setpoint")
    high_temp_inhibit_offset: Temperature = Field(description="High temp inhibit offset")
    low_temp_inhibit_offset: Temperature = Field(description="Low temp inhibit offset")
    fixed_high_temp_alarm: Temperature = Field(description="Fixed high temperature alarm")
    fixed_low_temp_alarm: Temperature = Field(description="Fixed low temperature alarm")

    # Control settings
    interlock_bits: int = Field(ge=0, description="Interlock configuration bits")
    zone_bits: int = Field(ge=0, description="Zone configuration bits")
    temperature_control: int = Field(ge=0, le=255, description="Temperature control mode")

    # Humidity settings
    humidity_setpoint: int = Field(ge=0, le=100, description="Humidity setpoint percentage")
    humidity_off_time: int = Field(ge=0, description="Humidity off time in seconds")
    humidity_purge_time: int = Field(ge=0, description="Humidity purge time in seconds")

    # Animal/production information
    animal_age: int = Field(ge=0, description="Current animal age in days")
    projected_age: int = Field(ge=0, description="Projected end age in days")
    weight: int = Field(ge=0, description="Animal weight")
    begin_head_count: int = Field(ge=0, description="Beginning head count")
    mortality_count: int = Field(ge=0, description="Mortality count")
    sold_count: int = Field(ge=0, description="Sold count")

    # Long head counts (format 3+ with extended records)
    begin_head_count_long: int = Field(default=0, ge=0, description="Long beginning head count")
    mortality_count_long: int = Field(default=0, ge=0, description="Long mortality count")
    sold_count_long: int = Field(default=0, ge=0, description="Long sold count")
    uses_long_head_counts: bool = Field(default=False, description="Uses 32-bit head counts")

    # Original data
    raw_data: str | None = Field(default=None, description="Original hex data")


class ZoneVariables(BaseModel):
    """
    Zone variable record containing real-time readings for a zone.

    Zone variables contain the current state and measurements for a zone,
    including actual temperatures, timer states, and device statuses.
    """

    model_config = ConfigDict(frozen=True)

    # Header
    record_size_words: int = Field(ge=0, description="Record size in words")
    zone_number: int = Field(ge=1, le=9, description="Zone number (1-9)")
    record_type: int = Field(ge=0, le=255, description="Record type code")
    record_format: int = Field(ge=0, le=255, description="Record format version")

    # Temperature readings
    actual_temperature: Temperature = Field(description="Current actual temperature")
    setpoint_temperature: Temperature = Field(description="Current effective setpoint")
    outside_temperature: Temperature = Field(description="Outside temperature")

    # Humidity readings
    actual_humidity: int = Field(ge=0, le=100, description="Current humidity percentage")

    # Timer states
    current_age_days: int = Field(ge=0, description="Current age in days")
    lights_on_minutes: int = Field(ge=0, description="Minutes until lights on")
    lights_off_minutes: int = Field(ge=0, description="Minutes until lights off")

    # Status flags
    alarm_status: int = Field(ge=0, description="Active alarm flags")
    zone_status: int = Field(ge=0, description="Zone status flags")

    # Original data
    raw_data: str | None = Field(default=None, description="Original hex data")


class AlarmRecord(BaseModel):
    """
    Alarm record from the controller's alarm log.

    Contains information about an alarm event including type, timestamp,
    zone, and status.
    """

    model_config = ConfigDict(frozen=True)

    # Header
    alarm_type: int = Field(ge=0, le=255, description="Alarm type code")
    alarm_subtype: int = Field(ge=0, le=255, description="Alarm subtype")
    zone_number: int = Field(ge=0, le=9, description="Zone number (0 = controller)")
    occurrence: int = Field(ge=0, description="Occurrence count")

    # Timestamp (encoded as controller format)
    timestamp_raw: int = Field(ge=0, description="Raw timestamp value")

    # Status
    is_active: bool = Field(description="Alarm is currently active")
    is_acknowledged: bool = Field(description="Alarm has been acknowledged")

    # Original data
    raw_data: str | None = Field(default=None, description="Original hex data")


class HistoryRecord(BaseModel):
    """
    History record containing a daily snapshot of zone data.

    History records are stored daily and contain summary information
    about zone conditions including temperature ranges, production data,
    and equipment runtime.
    """

    model_config = ConfigDict(frozen=True)

    # Header
    zone_number: int = Field(ge=1, le=9, description="Zone number")
    day_of_year: int = Field(ge=1, le=366, description="Day of year (1-366)")
    year: int = Field(ge=0, description="Year")

    # Temperature data
    high_temperature: Temperature = Field(description="High temperature for day")
    low_temperature: Temperature = Field(description="Low temperature for day")
    average_temperature: Temperature = Field(description="Average temperature")

    # Production data
    mortality: int = Field(ge=0, description="Mortality for day")
    water_usage: int = Field(ge=0, description="Water usage")
    feed_usage: int = Field(ge=0, description="Feed usage")

    # Original data
    raw_data: str | None = Field(default=None, description="Original hex data")
