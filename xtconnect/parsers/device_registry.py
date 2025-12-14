"""
Device parser registry and strategy interfaces.

This module implements the Strategy pattern for device-specific parsing.
Each device type (fan, heater, inlet, etc.) can have specialized parsing
logic registered with the DeviceParserRegistry.

The registry allows:
- Registration of custom parsing strategies per device type
- Fallback to generic parsing for unknown device types
- Separation of parsing logic from the main parser flow

Architecture:
    DeviceParserRegistry
        ├── DeviceParameterStrategy (interface)
        │   ├── FanParameterStrategy
        │   ├── HeaterParameterStrategy
        │   └── ... (21 device types)
        └── DeviceVariableStrategy (interface)
            ├── FanVariableStrategy
            ├── HeaterVariableStrategy
            └── ...
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from xtconnect.models.records import DeviceRecordHeader, DeviceType

if TYPE_CHECKING:
    from xtconnect.parsers.hex_reader import HexStringReader


# Type variables for generic device data
TParams = TypeVar("TParams")
TVars = TypeVar("TVars")


@dataclass(frozen=True)
class GenericDeviceParameters:
    """
    Generic device parameters for unrecognized device types.

    Used as a fallback when no specific strategy is registered.
    Contains the raw hex data for later analysis.
    """

    header: DeviceRecordHeader
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type from the header."""
        return self.header.device_type


@dataclass(frozen=True)
class GenericDeviceVariables:
    """
    Generic device variables for unrecognized device types.

    Used as a fallback when no specific strategy is registered.
    """

    header: DeviceRecordHeader
    raw_data: str

    @property
    def device_type(self) -> DeviceType:
        """Get the device type from the header."""
        return self.header.device_type


class DeviceParameterStrategy(ABC):
    """
    Abstract base class for device parameter parsing strategies.

    Each device type can have a specialized strategy that knows how to
    parse the device-specific parameter fields from the hex data.

    Implementations should:
    1. Define the device_type property
    2. Implement parse() to extract device-specific parameters
    3. Return an immutable dataclass/model with the parsed data
    """

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """
        The device type this strategy handles.

        Returns:
            DeviceType enum value.
        """
        ...

    @abstractmethod
    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> Any:
        """
        Parse device-specific parameters from the hex data.

        The reader is positioned after the common header fields.
        The implementation should read device-specific fields and
        return an appropriate data structure.

        Args:
            reader: HexStringReader positioned after header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data (for storage/debugging).

        Returns:
            Device-specific parameter object.
        """
        ...


class DeviceVariableStrategy(ABC):
    """
    Abstract base class for device variable parsing strategies.

    Similar to DeviceParameterStrategy but for runtime variable data.
    Device variables contain current state and measurements.
    """

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """The device type this strategy handles."""
        ...

    @abstractmethod
    def parse(
        self,
        reader: HexStringReader,
        header: DeviceRecordHeader,
        raw_data: str,
    ) -> Any:
        """
        Parse device-specific variables from the hex data.

        Args:
            reader: HexStringReader positioned after header.
            header: Already-parsed device record header.
            raw_data: Complete raw hex data.

        Returns:
            Device-specific variable object.
        """
        ...


class DeviceParserRegistry:
    """
    Registry for device-specific parsing strategies.

    The registry maintains mappings from DeviceType to parsing strategies.
    When parsing device records, the appropriate strategy is looked up
    and used to parse device-specific fields.

    If no strategy is registered for a device type, the registry returns
    None and the caller should use generic parsing.

    Example:
        >>> registry = DeviceParserRegistry()
        >>> registry.register_parameter_strategy(FanParameterStrategy())
        >>> strategy = registry.get_parameter_strategy(DeviceType.FAN)
        >>> if strategy:
        ...     params = strategy.parse(reader, header, raw_data)
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._parameter_strategies: dict[DeviceType, DeviceParameterStrategy] = {}
        self._variable_strategies: dict[DeviceType, DeviceVariableStrategy] = {}

    def register_parameter_strategy(
        self,
        strategy: DeviceParameterStrategy,
    ) -> None:
        """
        Register a device parameter parsing strategy.

        Args:
            strategy: Strategy instance to register.

        Note:
            Replaces any existing strategy for the same device type.
        """
        self._parameter_strategies[strategy.device_type] = strategy

    def register_variable_strategy(
        self,
        strategy: DeviceVariableStrategy,
    ) -> None:
        """
        Register a device variable parsing strategy.

        Args:
            strategy: Strategy instance to register.
        """
        self._variable_strategies[strategy.device_type] = strategy

    def get_parameter_strategy(
        self,
        device_type: DeviceType,
    ) -> DeviceParameterStrategy | None:
        """
        Get the parameter parsing strategy for a device type.

        Args:
            device_type: The device type to look up.

        Returns:
            Strategy if registered, None otherwise.
        """
        return self._parameter_strategies.get(device_type)

    def get_variable_strategy(
        self,
        device_type: DeviceType,
    ) -> DeviceVariableStrategy | None:
        """
        Get the variable parsing strategy for a device type.

        Args:
            device_type: The device type to look up.

        Returns:
            Strategy if registered, None otherwise.
        """
        return self._variable_strategies.get(device_type)

    def has_parameter_strategy(self, device_type: DeviceType) -> bool:
        """Check if a parameter strategy is registered."""
        return device_type in self._parameter_strategies

    def has_variable_strategy(self, device_type: DeviceType) -> bool:
        """Check if a variable strategy is registered."""
        return device_type in self._variable_strategies

    @property
    def registered_parameter_types(self) -> frozenset[DeviceType]:
        """Get all device types with registered parameter strategies."""
        return frozenset(self._parameter_strategies.keys())

    @property
    def registered_variable_types(self) -> frozenset[DeviceType]:
        """Get all device types with registered variable strategies."""
        return frozenset(self._variable_strategies.keys())

    def unregister_parameter_strategy(self, device_type: DeviceType) -> bool:
        """
        Remove a parameter strategy registration.

        Args:
            device_type: Device type to unregister.

        Returns:
            True if a strategy was removed, False if none was registered.
        """
        if device_type in self._parameter_strategies:
            del self._parameter_strategies[device_type]
            return True
        return False

    def unregister_variable_strategy(self, device_type: DeviceType) -> bool:
        """
        Remove a variable strategy registration.

        Args:
            device_type: Device type to unregister.

        Returns:
            True if a strategy was removed, False if none was registered.
        """
        if device_type in self._variable_strategies:
            del self._variable_strategies[device_type]
            return True
        return False

    def clear(self) -> None:
        """Remove all registered strategies."""
        self._parameter_strategies.clear()
        self._variable_strategies.clear()

    def __repr__(self) -> str:
        return (
            f"DeviceParserRegistry("
            f"params={len(self._parameter_strategies)}, "
            f"vars={len(self._variable_strategies)})"
        )


def parse_device_record_header(reader: HexStringReader) -> DeviceRecordHeader:
    """
    Parse the common device record header.

    The header is the same structure for both parameter and variable records.
    After calling this, the reader is positioned at the device-specific data.

    Args:
        reader: HexStringReader at the start of the record.

    Returns:
        Parsed DeviceRecordHeader.

    Header structure (8 bytes):
        - record_size_words: uint16 (2 bytes)
        - zone_number: byte (1 byte)
        - record_type: byte (1 byte)
        - record_format: byte upper nibble, device_subtype lower nibble (1 byte)
        - device_type: byte (1 byte)
        - module_address: byte (1 byte)
        - channel_number: byte (1 byte)
    """
    record_size_words = reader.read_uint16()
    zone_number = reader.read_byte()
    record_type = reader.read_byte()

    format_subtype_byte = reader.read_byte()
    record_format = (format_subtype_byte >> 4) & 0x0F
    device_subtype = format_subtype_byte & 0x0F

    device_type_byte = reader.read_byte()
    try:
        device_type = DeviceType(device_type_byte)
    except ValueError:
        device_type = DeviceType.UNKNOWN

    module_address = reader.read_byte()
    channel_number = reader.read_byte()

    return DeviceRecordHeader(
        record_size_words=record_size_words,
        zone_number=zone_number,
        record_type=record_type,
        record_format=record_format,
        device_type=device_type,
        device_subtype=device_subtype,
        module_address=module_address,
        channel_number=channel_number,
    )


# Default global registry instance
DEFAULT_REGISTRY = DeviceParserRegistry()
"""Default device parser registry. Can be used directly or as a template."""


def create_default_registry() -> DeviceParserRegistry:
    """
    Create a new registry with all built-in device strategies registered.

    Registers strategies for all 20 device types:
    - Sensors: AirSensor, HumiditySensor, StaticSensor, DigitalSensor,
               PositionSensor, FeedSensor, WaterSensor, GasSensor
    - Positional: Inlet, Curtain, RidgeVent, Chimney
    - Climate: Heater, CoolPad, Fan, VariableHeater, VfdFan
    - Other: Timed, Switch, V10Lights

    Returns:
        DeviceParserRegistry with all built-in strategies.
    """
    from xtconnect.parsers.devices import register_all_strategies

    registry = DeviceParserRegistry()
    register_all_strategies(registry)
    return registry
