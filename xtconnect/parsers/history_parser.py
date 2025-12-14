"""
History record parser.

History records contain timestamped environmental data logged by the
controller at regular intervals. Each history group represents a
different data point (temperature, humidity, etc.).

The controller stores multiple samples per history group, with
timestamps encoded as offsets from a base date (1980-01-01).
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


class HistoryGroup(IntEnum):
    """History data group types."""

    TEMPERATURE = 1
    """Zone temperature readings."""

    HUMIDITY = 2
    """Zone humidity readings."""

    SETPOINT = 3
    """Temperature setpoint values."""

    OUTSIDE_TEMP = 4
    """Outside temperature readings."""

    STATIC_PRESSURE = 5
    """Static pressure readings."""

    WATER_USAGE = 6
    """Water consumption data."""

    FEED_USAGE = 7
    """Feed consumption data."""

    MORTALITY = 8
    """Mortality count data."""

    WEIGHT = 9
    """Animal weight data."""


@dataclass(frozen=True)
class HistorySample:
    """
    A single history data sample.

    Attributes:
        timestamp: When the sample was recorded.
        value: The recorded value (interpretation depends on group).
        raw_value: Raw integer value from controller.
    """

    timestamp: datetime
    value: float
    raw_value: int

    @property
    def is_valid(self) -> bool:
        """Check if sample has valid data."""
        return self.raw_value != 0x7FFF


@dataclass(frozen=True)
class HistoryRecord:
    """
    A history record containing multiple samples for a group.

    Attributes:
        zone_number: Zone this history belongs to.
        group: Type of history data.
        interval_minutes: Sampling interval in minutes.
        samples: List of data samples.
        raw_data: Original hex data for debugging.
    """

    zone_number: int
    group: int
    interval_minutes: int
    sample_count: int
    start_timestamp: datetime
    samples: list[HistorySample]
    raw_data: str

    @property
    def history_group(self) -> HistoryGroup:
        """Get the history group as enum."""
        try:
            return HistoryGroup(self.group)
        except ValueError:
            return HistoryGroup.TEMPERATURE

    @property
    def end_timestamp(self) -> datetime:
        """Calculate end timestamp from samples."""
        if not self.samples:
            return self.start_timestamp
        return self.samples[-1].timestamp


class HistoryRecordParser:
    """
    Parser for history records.

    History record structure:
    - Zone number (1 byte)
    - History group (1 byte)
    - Interval minutes (2 bytes)
    - Sample count (2 bytes)
    - Start timestamp (4 bytes, minutes since 1980-01-01)
    - Samples (2 bytes each)
    """

    # Base date for timestamp calculations
    BASE_DATE = datetime(ProtocolConstants.BASE_YEAR_FOR_DATES, 1, 1)

    def parse(
        self,
        hex_data: str,
        endian_strategy: EndianStrategy,
    ) -> HistoryRecord:
        """
        Parse a history record from hex data.

        Args:
            hex_data: Hex-encoded history record data.
            endian_strategy: Endianness strategy for multi-byte values.

        Returns:
            Parsed HistoryRecord.
        """
        from xtconnect.parsers.hex_reader import HexStringReader

        reader = HexStringReader(hex_data, endian_strategy)

        zone_number = reader.read_byte()
        group = reader.read_byte()
        interval_minutes = reader.read_uint16()
        sample_count = reader.read_uint16()
        start_minutes = reader.read_uint32()

        # Calculate start timestamp
        start_timestamp = self.BASE_DATE + timedelta(minutes=start_minutes)

        # Parse samples
        samples: list[HistorySample] = []
        for i in range(sample_count):
            if reader.remaining < 4:  # 2 bytes = 4 hex chars
                break

            raw_value = reader.read_int16()
            sample_time = start_timestamp + timedelta(minutes=i * interval_minutes)

            # Convert raw value based on group type
            if group in (HistoryGroup.TEMPERATURE, HistoryGroup.SETPOINT, HistoryGroup.OUTSIDE_TEMP):
                # Temperature: tenths of degree
                value = raw_value / 10.0
            elif group == HistoryGroup.HUMIDITY:
                # Humidity: percentage
                value = float(raw_value)
            elif group == HistoryGroup.STATIC_PRESSURE:
                # Static pressure: hundredths of inch WC
                value = raw_value / 100.0
            else:
                # Other values: use raw
                value = float(raw_value)

            samples.append(HistorySample(
                timestamp=sample_time,
                value=value,
                raw_value=raw_value,
            ))

        return HistoryRecord(
            zone_number=zone_number,
            group=group,
            interval_minutes=interval_minutes,
            sample_count=sample_count,
            start_timestamp=start_timestamp,
            samples=samples,
            raw_data=hex_data,
        )


def parse_history_record(
    hex_data: str,
    endian_strategy: EndianStrategy | None = None,
) -> HistoryRecord:
    """
    Convenience function to parse a history record.

    Args:
        hex_data: Hex-encoded history record data.
        endian_strategy: Endianness strategy (defaults to NonSwap).

    Returns:
        Parsed HistoryRecord.
    """
    from xtconnect.protocol.endianness import NON_SWAP_STRATEGY

    strategy = endian_strategy or NON_SWAP_STRATEGY
    parser = HistoryRecordParser()
    return parser.parse(hex_data, strategy)
