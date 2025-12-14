"""
Zone parameter and variable record parsers.

This module provides parsers for zone-level data from Valco controllers.
Zone records contain configuration (parameters) and runtime data (variables)
for each zone in the controller.

Zone Parameter Record:
- Temperature setpoints and alarm thresholds
- Humidity settings
- Control configuration bits
- Animal/production information (age, weight, head counts)

Zone Variable Record:
- Current temperatures and humidity
- Timer states
- Alarm and status flags

Record Format Versions:
- Format < 20: Big-endian (Swap), older VP controllers
- Format >= 20: Little-endian (NonSwap), VPII and XT controllers
- Format 3+: Extended head counts (32-bit)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from xtconnect.exceptions import ParseError
from xtconnect.models.records import (
    Temperature,
    ZoneParameters,
    ZoneVariables,
)
from xtconnect.parsers.hex_reader import HexStringReader
from xtconnect.protocol.endianness import get_endian_strategy

if TYPE_CHECKING:
    from xtconnect.protocol.endianness import EndianStrategy


class ZoneParameterParser:
    """
    Parser for zone parameter records.

    Zone parameters contain the configuration settings for a zone,
    including temperature setpoints, alarm thresholds, control modes,
    and animal production data.

    The parser handles different record format versions automatically,
    selecting the appropriate endianness strategy based on the format.

    Example:
        >>> parser = ZoneParameterParser()
        >>> zone_params = parser.parse("001A0114...")  # hex data
        >>> print(zone_params.temp_setpoint.fahrenheit)
        72.5
    """

    # Byte offsets for zone parameter fields (in bytes, not hex chars)
    # These are based on the .NET ZoneParameterParser implementation

    # Header (common to all formats)
    OFFSET_RECORD_SIZE = 0       # 2 bytes - record size in words
    OFFSET_ZONE_NUMBER = 2       # 1 byte
    OFFSET_RECORD_TYPE = 3       # 1 byte
    OFFSET_RECORD_FORMAT = 4     # 1 byte (high nibble)
    OFFSET_TEMP_CONTROL = 4      # 1 byte (low nibble)

    # Temperature settings
    OFFSET_TEMP_SETPOINT = 6             # 2 bytes - int16
    OFFSET_HIGH_TEMP_ALARM = 8           # 2 bytes - int16
    OFFSET_LOW_TEMP_ALARM = 10           # 2 bytes - int16
    OFFSET_HIGH_TEMP_INHIBIT = 12        # 2 bytes - int16
    OFFSET_LOW_TEMP_INHIBIT = 14         # 2 bytes - int16
    OFFSET_FIXED_HIGH_TEMP = 16          # 2 bytes - int16
    OFFSET_FIXED_LOW_TEMP = 18           # 2 bytes - int16

    # Control settings
    OFFSET_INTERLOCK_BITS = 20           # 2 bytes - uint16
    OFFSET_ZONE_BITS = 22                # 2 bytes - uint16

    # Humidity settings
    OFFSET_HUMIDITY_SETPOINT = 24        # 1 byte
    OFFSET_HUMIDITY_OFF_TIME = 26        # 2 bytes - uint16
    OFFSET_HUMIDITY_PURGE_TIME = 28      # 2 bytes - uint16

    # Animal information
    OFFSET_ANIMAL_AGE = 30               # 2 bytes - uint16
    OFFSET_PROJECTED_AGE = 32            # 2 bytes - uint16
    OFFSET_WEIGHT = 34                   # 2 bytes - uint16
    OFFSET_BEGIN_HEAD_COUNT = 36         # 2 bytes - uint16 (word)
    OFFSET_MORTALITY_COUNT = 38          # 2 bytes - uint16 (word)
    OFFSET_SOLD_COUNT = 40               # 2 bytes - uint16 (word)

    # Extended head counts (format 3+)
    OFFSET_BEGIN_HEAD_COUNT_LONG = 42    # 4 bytes - uint32
    OFFSET_MORTALITY_COUNT_LONG = 46     # 4 bytes - uint32
    OFFSET_SOLD_COUNT_LONG = 50          # 4 bytes - uint32

    # Minimum record sizes
    MIN_RECORD_SIZE_BASIC = 42           # Without long head counts
    MIN_RECORD_SIZE_EXTENDED = 54        # With long head counts

    def parse(
        self,
        hex_data: str,
        endian_strategy: EndianStrategy | None = None,
    ) -> ZoneParameters:
        """
        Parse zone parameters from hex-encoded data.

        Args:
            hex_data: Hex-encoded zone parameter record.
            endian_strategy: Optional override for endianness. If None,
                           determined from record format field.

        Returns:
            Parsed ZoneParameters object.

        Raises:
            ParseError: If data is invalid or incomplete.
        """
        if len(hex_data) < self.MIN_RECORD_SIZE_BASIC * 2:
            raise ParseError(
                f"Zone parameter data too short: {len(hex_data)} chars, "
                f"need at least {self.MIN_RECORD_SIZE_BASIC * 2}",
                record_type="ZoneParameters",
                raw_data=hex_data,
            )

        # First, peek at the record format to determine endianness
        # Record format is in byte 4, upper nibble
        try:
            format_byte = int(hex_data[8:10], 16)
            record_format = (format_byte >> 4) & 0x0F
            temp_control = format_byte & 0x0F
        except (ValueError, IndexError) as e:
            raise ParseError(
                "Cannot read record format",
                record_type="ZoneParameters",
                raw_data=hex_data,
            ) from e

        # Determine endianness strategy
        if endian_strategy is None:
            endian_strategy = get_endian_strategy(record_format)

        reader = HexStringReader(hex_data, endian_strategy)

        try:
            return self._parse_with_reader(reader, hex_data, record_format, temp_control)
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(
                f"Failed to parse zone parameters: {e}",
                record_type="ZoneParameters",
                offset=reader.position,
                raw_data=hex_data,
            ) from e

    def _parse_with_reader(
        self,
        reader: HexStringReader,
        raw_data: str,
        record_format: int,
        temp_control: int,
    ) -> ZoneParameters:
        """Internal parsing logic using HexStringReader."""
        # Header
        record_size_words = reader.read_uint16()
        zone_number = reader.read_byte()
        record_type = reader.read_byte()
        reader.skip_bytes(1)  # Already read format byte, skip it
        reader.skip_bytes(1)  # Padding/reserved byte

        # Temperature settings
        temp_setpoint = Temperature(raw_value=reader.read_int16())
        high_temp_alarm_offset = Temperature(raw_value=reader.read_int16())
        low_temp_alarm_offset = Temperature(raw_value=reader.read_int16())
        high_temp_inhibit_offset = Temperature(raw_value=reader.read_int16())
        low_temp_inhibit_offset = Temperature(raw_value=reader.read_int16())
        fixed_high_temp_alarm = Temperature(raw_value=reader.read_int16())
        fixed_low_temp_alarm = Temperature(raw_value=reader.read_int16())

        # Control settings
        interlock_bits = reader.read_uint16()
        zone_bits = reader.read_uint16()

        # Humidity settings
        humidity_setpoint = reader.read_byte()
        reader.skip_bytes(1)  # Padding
        humidity_off_time = reader.read_uint16()
        humidity_purge_time = reader.read_uint16()

        # Animal information
        animal_age = reader.read_uint16()
        projected_age = reader.read_uint16()
        weight = reader.read_uint16()
        begin_head_count = reader.read_uint16()
        mortality_count = reader.read_uint16()
        sold_count = reader.read_uint16()

        # Extended head counts (format 3+)
        uses_long_head_counts = False
        begin_head_count_long = 0
        mortality_count_long = 0
        sold_count_long = 0

        if record_format >= 3 and reader.remaining_bytes >= 12:
            uses_long_head_counts = True
            begin_head_count_long = reader.read_uint32()
            mortality_count_long = reader.read_uint32()
            sold_count_long = reader.read_uint32()

        return ZoneParameters(
            record_size_words=record_size_words,
            zone_number=zone_number,
            record_type=record_type,
            record_format=record_format,
            temp_setpoint=temp_setpoint,
            high_temp_alarm_offset=high_temp_alarm_offset,
            low_temp_alarm_offset=low_temp_alarm_offset,
            high_temp_inhibit_offset=high_temp_inhibit_offset,
            low_temp_inhibit_offset=low_temp_inhibit_offset,
            fixed_high_temp_alarm=fixed_high_temp_alarm,
            fixed_low_temp_alarm=fixed_low_temp_alarm,
            interlock_bits=interlock_bits,
            zone_bits=zone_bits,
            temperature_control=temp_control,
            humidity_setpoint=humidity_setpoint,
            humidity_off_time=humidity_off_time,
            humidity_purge_time=humidity_purge_time,
            animal_age=animal_age,
            projected_age=projected_age,
            weight=weight,
            begin_head_count=begin_head_count,
            mortality_count=mortality_count,
            sold_count=sold_count,
            begin_head_count_long=begin_head_count_long,
            mortality_count_long=mortality_count_long,
            sold_count_long=sold_count_long,
            uses_long_head_counts=uses_long_head_counts,
            raw_data=raw_data,
        )


class ZoneVariableParser:
    """
    Parser for zone variable records.

    Zone variables contain the runtime state for a zone, including
    current temperatures, humidity, timer states, and status flags.

    Example:
        >>> parser = ZoneVariableParser()
        >>> zone_vars = parser.parse("001A0114...")
        >>> print(zone_vars.actual_temperature.fahrenheit)
        73.2
    """

    # Byte offsets for zone variable fields
    OFFSET_RECORD_SIZE = 0           # 2 bytes - record size in words
    OFFSET_ZONE_NUMBER = 2           # 1 byte
    OFFSET_RECORD_TYPE = 3           # 1 byte
    OFFSET_RECORD_FORMAT = 4         # 1 byte (high nibble)

    OFFSET_ACTUAL_TEMP = 6           # 2 bytes - int16
    OFFSET_SETPOINT_TEMP = 8         # 2 bytes - int16
    OFFSET_OUTSIDE_TEMP = 10         # 2 bytes - int16
    OFFSET_ACTUAL_HUMIDITY = 12      # 1 byte
    OFFSET_CURRENT_AGE = 14          # 2 bytes - uint16
    OFFSET_LIGHTS_ON_MINUTES = 16    # 2 bytes - uint16
    OFFSET_LIGHTS_OFF_MINUTES = 18   # 2 bytes - uint16
    OFFSET_ALARM_STATUS = 20         # 2 bytes - uint16
    OFFSET_ZONE_STATUS = 22          # 2 bytes - uint16

    MIN_RECORD_SIZE = 24

    def parse(
        self,
        hex_data: str,
        endian_strategy: EndianStrategy | None = None,
    ) -> ZoneVariables:
        """
        Parse zone variables from hex-encoded data.

        Args:
            hex_data: Hex-encoded zone variable record.
            endian_strategy: Optional override for endianness.

        Returns:
            Parsed ZoneVariables object.

        Raises:
            ParseError: If data is invalid or incomplete.
        """
        if len(hex_data) < self.MIN_RECORD_SIZE * 2:
            raise ParseError(
                f"Zone variable data too short: {len(hex_data)} chars, "
                f"need at least {self.MIN_RECORD_SIZE * 2}",
                record_type="ZoneVariables",
                raw_data=hex_data,
            )

        # Peek at record format for endianness
        try:
            format_byte = int(hex_data[8:10], 16)
            record_format = (format_byte >> 4) & 0x0F
        except (ValueError, IndexError) as e:
            raise ParseError(
                "Cannot read record format",
                record_type="ZoneVariables",
                raw_data=hex_data,
            ) from e

        if endian_strategy is None:
            endian_strategy = get_endian_strategy(record_format)

        reader = HexStringReader(hex_data, endian_strategy)

        try:
            return self._parse_with_reader(reader, hex_data, record_format)
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(
                f"Failed to parse zone variables: {e}",
                record_type="ZoneVariables",
                offset=reader.position,
                raw_data=hex_data,
            ) from e

    def _parse_with_reader(
        self,
        reader: HexStringReader,
        raw_data: str,
        record_format: int,
    ) -> ZoneVariables:
        """Internal parsing logic using HexStringReader."""
        # Header
        record_size_words = reader.read_uint16()
        zone_number = reader.read_byte()
        record_type = reader.read_byte()
        reader.skip_bytes(2)  # Format byte and padding

        # Temperature readings
        actual_temperature = Temperature(raw_value=reader.read_int16())
        setpoint_temperature = Temperature(raw_value=reader.read_int16())
        outside_temperature = Temperature(raw_value=reader.read_int16())

        # Humidity
        actual_humidity = reader.read_byte()
        reader.skip_bytes(1)  # Padding

        # Timer states
        current_age_days = reader.read_uint16()
        lights_on_minutes = reader.read_uint16()
        lights_off_minutes = reader.read_uint16()

        # Status flags
        alarm_status = reader.read_uint16()
        zone_status = reader.read_uint16()

        return ZoneVariables(
            record_size_words=record_size_words,
            zone_number=zone_number,
            record_type=record_type,
            record_format=record_format,
            actual_temperature=actual_temperature,
            setpoint_temperature=setpoint_temperature,
            outside_temperature=outside_temperature,
            actual_humidity=actual_humidity,
            current_age_days=current_age_days,
            lights_on_minutes=lights_on_minutes,
            lights_off_minutes=lights_off_minutes,
            alarm_status=alarm_status,
            zone_status=zone_status,
            raw_data=raw_data,
        )


# Module-level parser instances for convenience
DEFAULT_ZONE_PARAMETER_PARSER = ZoneParameterParser()
DEFAULT_ZONE_VARIABLE_PARSER = ZoneVariableParser()


def parse_zone_parameters(
    hex_data: str,
    endian_strategy: EndianStrategy | None = None,
) -> ZoneParameters:
    """
    Parse zone parameters using the default parser.

    Convenience function for quick parsing without creating a parser instance.

    Args:
        hex_data: Hex-encoded zone parameter record.
        endian_strategy: Optional endianness override.

    Returns:
        Parsed ZoneParameters object.
    """
    return DEFAULT_ZONE_PARAMETER_PARSER.parse(hex_data, endian_strategy)


def parse_zone_variables(
    hex_data: str,
    endian_strategy: EndianStrategy | None = None,
) -> ZoneVariables:
    """
    Parse zone variables using the default parser.

    Convenience function for quick parsing without creating a parser instance.

    Args:
        hex_data: Hex-encoded zone variable record.
        endian_strategy: Optional endianness override.

    Returns:
        Parsed ZoneVariables object.
    """
    return DEFAULT_ZONE_VARIABLE_PARSER.parse(hex_data, endian_strategy)
