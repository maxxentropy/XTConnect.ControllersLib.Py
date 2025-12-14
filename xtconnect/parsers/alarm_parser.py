"""
Alarm record parser.

Alarm records contain information about active and historical alarms
in the controller. Each alarm has a type, zone, timestamp, and
associated values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
from typing import TYPE_CHECKING

from xtconnect.models.records import Temperature
from xtconnect.protocol.constants import ProtocolConstants

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader
    from xtconnect.protocol.endianness import EndianStrategy


class AlarmType(IntEnum):
    """Alarm type codes."""

    NONE = 0
    """No alarm."""

    HIGH_TEMP = 1
    """High temperature alarm."""

    LOW_TEMP = 2
    """Low temperature alarm."""

    FIXED_HIGH_TEMP = 3
    """Fixed high temperature alarm."""

    FIXED_LOW_TEMP = 4
    """Fixed low temperature alarm."""

    HIGH_HUMIDITY = 5
    """High humidity alarm."""

    LOW_HUMIDITY = 6
    """Low humidity alarm."""

    POWER_FAILURE = 7
    """Power failure alarm."""

    POWER_RESTORED = 8
    """Power restored notification."""

    SENSOR_FAILURE = 9
    """Sensor failure alarm."""

    DEVICE_FAULT = 10
    """Device fault alarm."""

    HIGH_STATIC = 11
    """High static pressure alarm."""

    LOW_STATIC = 12
    """Low static pressure alarm."""

    HIGH_GAS = 13
    """High gas level alarm (NH3, CO2)."""

    WATER_FLOW = 14
    """Water flow alarm (high or low)."""

    FEED_LEVEL = 15
    """Feed level alarm (low)."""

    DOOR_OPEN = 16
    """Door open alarm."""

    GENERAL = 99
    """General/unspecified alarm."""


class AlarmState(IntEnum):
    """Alarm state values."""

    INACTIVE = 0
    """Alarm is no longer active."""

    ACTIVE = 1
    """Alarm is currently active."""

    ACKNOWLEDGED = 2
    """Alarm has been acknowledged by user."""

    CLEARED = 3
    """Alarm has been cleared."""


@dataclass(frozen=True)
class AlarmRecord:
    """
    An alarm record from the controller.

    Attributes:
        alarm_id: Unique identifier for this alarm instance.
        alarm_type: Type of alarm.
        zone_number: Zone where alarm occurred (0 = system-wide).
        device_index: Device index if device-specific alarm.
        state: Current alarm state.
        triggered_at: When the alarm was first triggered.
        cleared_at: When the alarm was cleared (if cleared).
        value: Alarm-related value (e.g., temperature that triggered).
        threshold: Threshold that was exceeded.
        raw_data: Original hex data for debugging.
    """

    alarm_id: int
    alarm_type: int
    zone_number: int
    device_index: int
    state: int
    triggered_at: datetime
    cleared_at: datetime | None
    value: int
    threshold: int
    raw_data: str

    @property
    def alarm_type_enum(self) -> AlarmType:
        """Get the alarm type as enum."""
        try:
            return AlarmType(self.alarm_type)
        except ValueError:
            return AlarmType.GENERAL

    @property
    def alarm_state(self) -> AlarmState:
        """Get the alarm state as enum."""
        try:
            return AlarmState(self.state)
        except ValueError:
            return AlarmState.INACTIVE

    @property
    def is_active(self) -> bool:
        """Check if alarm is currently active."""
        return self.state == AlarmState.ACTIVE

    @property
    def is_temperature_alarm(self) -> bool:
        """Check if this is a temperature-related alarm."""
        return self.alarm_type in (
            AlarmType.HIGH_TEMP,
            AlarmType.LOW_TEMP,
            AlarmType.FIXED_HIGH_TEMP,
            AlarmType.FIXED_LOW_TEMP,
        )

    @property
    def temperature_value(self) -> Temperature | None:
        """Get value as Temperature if this is a temperature alarm."""
        if self.is_temperature_alarm:
            return Temperature(raw_value=self.value)
        return None

    @property
    def temperature_threshold(self) -> Temperature | None:
        """Get threshold as Temperature if this is a temperature alarm."""
        if self.is_temperature_alarm:
            return Temperature(raw_value=self.threshold)
        return None


@dataclass(frozen=True)
class AlarmList:
    """
    List of alarm records from controller.

    Attributes:
        zone_number: Zone these alarms are for (0 = all zones).
        total_count: Total number of alarms in controller.
        alarms: List of alarm records.
        raw_data: Original hex data for debugging.
    """

    zone_number: int
    total_count: int
    alarms: list[AlarmRecord]
    raw_data: str

    @property
    def active_alarms(self) -> list[AlarmRecord]:
        """Get only active alarms."""
        return [a for a in self.alarms if a.is_active]

    @property
    def active_count(self) -> int:
        """Count of active alarms."""
        return len(self.active_alarms)

    def by_zone(self, zone: int) -> list[AlarmRecord]:
        """Get alarms for a specific zone."""
        return [a for a in self.alarms if a.zone_number == zone]

    def by_type(self, alarm_type: AlarmType) -> list[AlarmRecord]:
        """Get alarms of a specific type."""
        return [a for a in self.alarms if a.alarm_type == alarm_type]


class AlarmRecordParser:
    """
    Parser for alarm records.

    Alarm list structure:
    - Zone number (1 byte)
    - Reserved (1 byte)
    - Total alarm count (2 bytes)
    - Alarm records (variable)

    Each alarm record:
    - Alarm ID (2 bytes)
    - Alarm type (1 byte)
    - Zone number (1 byte)
    - Device index (2 bytes)
    - State (1 byte)
    - Reserved (1 byte)
    - Triggered timestamp (4 bytes, minutes since 1980)
    - Cleared timestamp (4 bytes, minutes since 1980, 0 = not cleared)
    - Value (2 bytes, int16)
    - Threshold (2 bytes, int16)
    """

    # Base date for timestamp calculations
    BASE_DATE = datetime(ProtocolConstants.BASE_YEAR_FOR_DATES, 1, 1)

    # Size of each alarm record in hex chars
    ALARM_RECORD_SIZE = 40  # 20 bytes * 2

    def parse(
        self,
        hex_data: str,
        endian_strategy: EndianStrategy,
    ) -> AlarmList:
        """
        Parse an alarm list from hex data.

        Args:
            hex_data: Hex-encoded alarm list data.
            endian_strategy: Endianness strategy for multi-byte values.

        Returns:
            Parsed AlarmList.
        """
        from xtconnect.parsers.hex_reader import HexStringReader

        reader = HexStringReader(hex_data, endian_strategy)

        zone_number = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        total_count = reader.read_uint16()

        alarms: list[AlarmRecord] = []

        # Parse each alarm record
        while reader.remaining >= self.ALARM_RECORD_SIZE:
            alarm_id = reader.read_uint16()
            alarm_type = reader.read_byte()
            alarm_zone = reader.read_byte()
            device_index = reader.read_uint16()
            state = reader.read_byte()
            reader.skip_bytes(1)  # Reserved

            triggered_minutes = reader.read_uint32()
            cleared_minutes = reader.read_uint32()

            value = reader.read_int16()
            threshold = reader.read_int16()

            # Calculate timestamps
            triggered_at = self.BASE_DATE + timedelta(minutes=triggered_minutes)
            cleared_at = None
            if cleared_minutes > 0:
                cleared_at = self.BASE_DATE + timedelta(minutes=cleared_minutes)

            alarms.append(AlarmRecord(
                alarm_id=alarm_id,
                alarm_type=alarm_type,
                zone_number=alarm_zone,
                device_index=device_index,
                state=state,
                triggered_at=triggered_at,
                cleared_at=cleared_at,
                value=value,
                threshold=threshold,
                raw_data=hex_data[reader.position - self.ALARM_RECORD_SIZE:reader.position],
            ))

        return AlarmList(
            zone_number=zone_number,
            total_count=total_count,
            alarms=alarms,
            raw_data=hex_data,
        )

    def parse_single(
        self,
        hex_data: str,
        endian_strategy: EndianStrategy,
    ) -> AlarmRecord:
        """
        Parse a single alarm record.

        Args:
            hex_data: Hex-encoded alarm record data.
            endian_strategy: Endianness strategy for multi-byte values.

        Returns:
            Parsed AlarmRecord.
        """
        from xtconnect.parsers.hex_reader import HexStringReader

        reader = HexStringReader(hex_data, endian_strategy)

        alarm_id = reader.read_uint16()
        alarm_type = reader.read_byte()
        alarm_zone = reader.read_byte()
        device_index = reader.read_uint16()
        state = reader.read_byte()
        reader.skip_bytes(1)  # Reserved

        triggered_minutes = reader.read_uint32()
        cleared_minutes = reader.read_uint32()

        value = reader.read_int16()
        threshold = reader.read_int16()

        triggered_at = self.BASE_DATE + timedelta(minutes=triggered_minutes)
        cleared_at = None
        if cleared_minutes > 0:
            cleared_at = self.BASE_DATE + timedelta(minutes=cleared_minutes)

        return AlarmRecord(
            alarm_id=alarm_id,
            alarm_type=alarm_type,
            zone_number=alarm_zone,
            device_index=device_index,
            state=state,
            triggered_at=triggered_at,
            cleared_at=cleared_at,
            value=value,
            threshold=threshold,
            raw_data=hex_data,
        )


def parse_alarm_list(
    hex_data: str,
    endian_strategy: EndianStrategy | None = None,
) -> AlarmList:
    """
    Convenience function to parse an alarm list.

    Args:
        hex_data: Hex-encoded alarm list data.
        endian_strategy: Endianness strategy (defaults to NonSwap).

    Returns:
        Parsed AlarmList.
    """
    from xtconnect.protocol.endianness import NON_SWAP_STRATEGY

    strategy = endian_strategy or NON_SWAP_STRATEGY
    parser = AlarmRecordParser()
    return parser.parse(hex_data, strategy)


def parse_alarm_record(
    hex_data: str,
    endian_strategy: EndianStrategy | None = None,
) -> AlarmRecord:
    """
    Convenience function to parse a single alarm record.

    Args:
        hex_data: Hex-encoded alarm record data.
        endian_strategy: Endianness strategy (defaults to NonSwap).

    Returns:
        Parsed AlarmRecord.
    """
    from xtconnect.protocol.endianness import NON_SWAP_STRATEGY

    strategy = endian_strategy or NON_SWAP_STRATEGY
    parser = AlarmRecordParser()
    return parser.parse_single(hex_data, strategy)
