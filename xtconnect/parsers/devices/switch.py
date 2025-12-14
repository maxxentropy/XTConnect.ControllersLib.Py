"""
Switch device parsing strategy.

Switches are simple on/off relay outputs that can be controlled
manually or based on interlock conditions. They're used for generic
equipment control.

Device Type: 16 (SWITCH)
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


class SwitchMode(IntEnum):
    """Switch operating modes."""

    OFF = 0
    """Switch is forced off."""

    AUTO = 1
    """Automatic control based on interlocks."""

    ON = 2
    """Switch is forced on."""


class SwitchStatus(IntEnum):
    """Switch runtime status values."""

    OFF = 0
    """Switch is currently off."""

    ON = 1
    """Switch is currently on."""

    INTERLOCKED = 2
    """Switch is off due to interlock condition."""


@dataclass(frozen=True)
class SwitchParameters:
    """
    Switch device parameters.

    Attributes:
        header: Common device record header.
        name_index: Index into name table for display name.
        mode: Operating mode (off, auto, on).
        min_on_time: Minimum on time in seconds.
        min_off_time: Minimum off time in seconds.
        control_bits: Control configuration flags.
        interlock_bits: Interlock configuration flags.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    name_index: int
    mode: int
    min_on_time: int
    min_off_time: int
    control_bits: int
    interlock_bits: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.SWITCH

    @property
    def zone_number(self) -> int:
        """Get the zone number from header."""
        return self.header.zone_number

    @property
    def switch_mode(self) -> SwitchMode:
        """Get the switch mode as enum."""
        try:
            return SwitchMode(self.mode)
        except ValueError:
            return SwitchMode.OFF


@dataclass(frozen=True)
class SwitchVariables:
    """
    Switch device variables (runtime data).

    Attributes:
        header: Common device record header.
        status: Current operating status.
        runtime_today: Total runtime today in minutes.
        cycles_today: Number of on/off cycles today.
        raw_data: Original hex data for debugging.
    """

    header: DeviceRecordHeader
    status: int
    runtime_today: int
    cycles_today: int
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type."""
        return DeviceType.SWITCH

    @property
    def switch_status(self) -> SwitchStatus:
        """Get the switch status as enum."""
        try:
            return SwitchStatus(self.status)
        except ValueError:
            return SwitchStatus.OFF

    @property
    def is_on(self) -> bool:
        """Check if switch is currently on."""
        return self.status == SwitchStatus.ON


class SwitchParameterStrategy(DeviceParameterStrategy):
    """
    Parsing strategy for switch parameters.

    Switch parameter record structure (after 8-byte header):
    - Name index (2 bytes)
    - Mode (1 byte)
    - Reserved (1 byte)
    - Min on time (2 bytes, seconds)
    - Min off time (2 bytes, seconds)
    - Control bits (2 bytes)
    - Interlock bits (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns SWITCH device type."""
        return DeviceType.SWITCH

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> SwitchParameters:
        """Parse switch parameters from hex data."""
        name_index = reader.read_uint16()
        mode = reader.read_byte()
        reader.skip_bytes(1)  # Reserved
        min_on_time = reader.read_uint16()
        min_off_time = reader.read_uint16()
        control_bits = reader.read_uint16()
        interlock_bits = reader.read_uint16()

        return SwitchParameters(
            header=header,
            name_index=name_index,
            mode=mode,
            min_on_time=min_on_time,
            min_off_time=min_off_time,
            control_bits=control_bits,
            interlock_bits=interlock_bits,
            raw_data=raw_data,
        )


class SwitchVariableStrategy(DeviceVariableStrategy):
    """
    Parsing strategy for switch variables.

    Switch variable record structure (after 8-byte header):
    - Status (2 bytes)
    - Runtime today (2 bytes, minutes)
    - Cycles today (2 bytes)
    """

    @property
    def device_type(self) -> DeviceType:
        """Returns SWITCH device type."""
        return DeviceType.SWITCH

    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> SwitchVariables:
        """Parse switch variables from hex data."""
        status = reader.read_uint16()
        runtime_today = reader.read_uint16()
        cycles_today = reader.read_uint16()

        return SwitchVariables(
            header=header,
            status=status,
            runtime_today=runtime_today,
            cycles_today=cycles_today,
            raw_data=raw_data,
        )
