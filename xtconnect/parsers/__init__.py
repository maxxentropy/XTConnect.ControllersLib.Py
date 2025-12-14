"""
Parsing engine for PCMI protocol records.

This package provides parsers for converting raw protocol data into
structured Python objects. The parsing architecture follows these principles:

1. **HexStringReader**: Low-level reader for navigating hex-encoded data
2. **Zone Parsers**: Parse zone parameter and variable records
3. **Device Registry**: Strategy pattern for device-specific parsing
4. **History Parser**: Parse timestamped environmental data
5. **Alarm Parser**: Parse alarm records and lists

The parsers handle both endianness modes (Swap/NonSwap) transparently
based on the record format version.

Example:
    >>> from xtconnect.parsers import HexStringReader, parse_zone_parameters
    >>> from xtconnect.protocol.endianness import NON_SWAP_STRATEGY
    >>>
    >>> # Parse zone parameters from hex data
    >>> zone_params = parse_zone_parameters(hex_data)
    >>> print(zone_params.temp_setpoint.fahrenheit)
"""

from xtconnect.parsers.alarm_parser import (
    AlarmList,
    AlarmRecord,
    AlarmRecordParser,
    AlarmState,
    AlarmType,
    parse_alarm_list,
    parse_alarm_record,
)
from xtconnect.parsers.device_registry import (
    DEFAULT_REGISTRY,
    DeviceParameterStrategy,
    DeviceParserRegistry,
    DeviceVariableStrategy,
    GenericDeviceParameters,
    GenericDeviceVariables,
    create_default_registry,
    parse_device_record_header,
)
from xtconnect.parsers.devices import (
    AirSensorParameters,
    AirSensorParameterStrategy,
    AirSensorVariables,
    AirSensorVariableStrategy,
    FanParameters,
    FanParameterStrategy,
    FanVariables,
    FanVariableStrategy,
    HeaterParameters,
    HeaterParameterStrategy,
    HeaterVariables,
    HeaterVariableStrategy,
    InletParameters,
    InletParameterStrategy,
    InletVariables,
    InletVariableStrategy,
    register_all_strategies,
)
from xtconnect.parsers.hex_reader import HexStringReader
from xtconnect.parsers.history_parser import (
    HistoryGroup,
    HistoryRecord,
    HistoryRecordParser,
    HistorySample,
    parse_history_record,
)
from xtconnect.parsers.zone_parser import (
    ZoneParameterParser,
    ZoneVariableParser,
    parse_zone_parameters,
    parse_zone_variables,
)

__all__ = [
    # Hex Reader
    "HexStringReader",
    # Zone Parsers
    "ZoneParameterParser",
    "ZoneVariableParser",
    "parse_zone_parameters",
    "parse_zone_variables",
    # History Parsers
    "HistoryRecordParser",
    "HistoryRecord",
    "HistorySample",
    "HistoryGroup",
    "parse_history_record",
    # Alarm Parsers
    "AlarmRecordParser",
    "AlarmRecord",
    "AlarmList",
    "AlarmType",
    "AlarmState",
    "parse_alarm_list",
    "parse_alarm_record",
    # Device Registry
    "DeviceParserRegistry",
    "DeviceParameterStrategy",
    "DeviceVariableStrategy",
    "GenericDeviceParameters",
    "GenericDeviceVariables",
    "parse_device_record_header",
    "create_default_registry",
    "DEFAULT_REGISTRY",
    # Device Strategies
    "AirSensorParameters",
    "AirSensorVariables",
    "AirSensorParameterStrategy",
    "AirSensorVariableStrategy",
    "FanParameters",
    "FanVariables",
    "FanParameterStrategy",
    "FanVariableStrategy",
    "HeaterParameters",
    "HeaterVariables",
    "HeaterParameterStrategy",
    "HeaterVariableStrategy",
    "InletParameters",
    "InletVariables",
    "InletParameterStrategy",
    "InletVariableStrategy",
    "register_all_strategies",
]
