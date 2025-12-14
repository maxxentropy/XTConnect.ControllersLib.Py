"""
Data models for PCMI protocol records.

This module contains Pydantic models representing the data structures
used in the PCMI protocol, including:

- Value objects (Temperature, SerialNumber, Humidity, etc.)
- Device types and subtypes
- Zone parameter and variable records
- Device parameter and variable records
- Alarm and history records
"""

from xtconnect.models.records import (
    DeviceRecordHeader,
    DeviceType,
    Humidity,
    SerialNumber,
    Temperature,
    TemperatureUnit,
    VersionRecord,
    ZoneParameters,
    ZoneVariables,
)

__all__ = [
    # Value Objects
    "Temperature",
    "TemperatureUnit",
    "SerialNumber",
    "Humidity",
    # Enums
    "DeviceType",
    # Records
    "VersionRecord",
    "ZoneParameters",
    "ZoneVariables",
    "DeviceRecordHeader",
]
