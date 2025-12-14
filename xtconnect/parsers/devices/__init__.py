"""
Device-specific parsing strategies.

This package contains strategy implementations for parsing device-specific
parameter and variable records. Each device type has its own module with
specialized parsing logic.

Supported device types (20 total):
- AirSensor (1): Temperature sensor devices
- HumiditySensor (2): Temperature and humidity sensors
- Inlet (3): Ventilation inlet controls
- Curtain (4): Side curtain controls
- RidgeVent (5): Ridge vent controls
- Heater (6): On/off heater controls
- CoolPad (7): Evaporative cooling pad controls
- Fan (8): Ventilation fan controls
- Timed (9): Timer-based device controls
- FeedSensor (10): Feed level sensors
- WaterSensor (11): Water flow sensors
- StaticSensor (12): Static pressure sensors
- DigitalSensor (13): Digital input sensors
- PositionSensor (14): Position feedback sensors
- Chimney (15): Natural ventilation chimney controls
- Switch (16): Generic switch/relay controls
- VariableHeater (25): Modulating heater controls
- VfdFan (26): Variable frequency drive fans
- V10Lights (27): Dimming light controls
- GasSensor (28): Gas level sensors (NH3, CO2)

Usage:
    >>> from xtconnect.parsers.devices import register_all_strategies
    >>> from xtconnect.parsers import DeviceParserRegistry
    >>> registry = DeviceParserRegistry()
    >>> register_all_strategies(registry)
"""

# Sensors
from xtconnect.parsers.devices.air_sensor import (
    AirSensorParameters,
    AirSensorParameterStrategy,
    AirSensorVariables,
    AirSensorVariableStrategy,
)
from xtconnect.parsers.devices.humidity_sensor import (
    HumiditySensorParameters,
    HumiditySensorParameterStrategy,
    HumiditySensorVariables,
    HumiditySensorVariableStrategy,
)
from xtconnect.parsers.devices.static_sensor import (
    StaticSensorParameters,
    StaticSensorParameterStrategy,
    StaticSensorVariables,
    StaticSensorVariableStrategy,
)
from xtconnect.parsers.devices.digital_sensor import (
    DigitalSensorParameters,
    DigitalSensorParameterStrategy,
    DigitalSensorVariables,
    DigitalSensorVariableStrategy,
)
from xtconnect.parsers.devices.position_sensor import (
    PositionSensorParameters,
    PositionSensorParameterStrategy,
    PositionSensorVariables,
    PositionSensorVariableStrategy,
)
from xtconnect.parsers.devices.feed_sensor import (
    FeedSensorParameters,
    FeedSensorParameterStrategy,
    FeedSensorVariables,
    FeedSensorVariableStrategy,
)
from xtconnect.parsers.devices.water_sensor import (
    WaterSensorParameters,
    WaterSensorParameterStrategy,
    WaterSensorVariables,
    WaterSensorVariableStrategy,
)
from xtconnect.parsers.devices.gas_sensor import (
    GasSensorParameters,
    GasSensorParameterStrategy,
    GasSensorVariables,
    GasSensorVariableStrategy,
)

# Positional devices
from xtconnect.parsers.devices.inlet import (
    InletParameters,
    InletParameterStrategy,
    InletVariables,
    InletVariableStrategy,
)
from xtconnect.parsers.devices.curtain import (
    CurtainParameters,
    CurtainParameterStrategy,
    CurtainVariables,
    CurtainVariableStrategy,
)
from xtconnect.parsers.devices.ridge_vent import (
    RidgeVentParameters,
    RidgeVentParameterStrategy,
    RidgeVentVariables,
    RidgeVentVariableStrategy,
)
from xtconnect.parsers.devices.chimney import (
    ChimneyParameters,
    ChimneyParameterStrategy,
    ChimneyVariables,
    ChimneyVariableStrategy,
)

# Climate control devices
from xtconnect.parsers.devices.heater import (
    HeaterParameters,
    HeaterParameterStrategy,
    HeaterVariables,
    HeaterVariableStrategy,
)
from xtconnect.parsers.devices.coolpad import (
    CoolPadParameters,
    CoolPadParameterStrategy,
    CoolPadVariables,
    CoolPadVariableStrategy,
)
from xtconnect.parsers.devices.fan import (
    FanParameters,
    FanParameterStrategy,
    FanVariables,
    FanVariableStrategy,
)
from xtconnect.parsers.devices.variable_heater import (
    VariableHeaterParameters,
    VariableHeaterParameterStrategy,
    VariableHeaterVariables,
    VariableHeaterVariableStrategy,
)
from xtconnect.parsers.devices.vfd_fan import (
    VfdFanParameters,
    VfdFanParameterStrategy,
    VfdFanVariables,
    VfdFanVariableStrategy,
)

# Other devices
from xtconnect.parsers.devices.timed import (
    TimedParameters,
    TimedParameterStrategy,
    TimedVariables,
    TimedVariableStrategy,
)
from xtconnect.parsers.devices.switch import (
    SwitchParameters,
    SwitchParameterStrategy,
    SwitchVariables,
    SwitchVariableStrategy,
)
from xtconnect.parsers.devices.v10_lights import (
    V10LightsParameters,
    V10LightsParameterStrategy,
    V10LightsVariables,
    V10LightsVariableStrategy,
)

__all__ = [
    # Sensors
    "AirSensorParameters",
    "AirSensorVariables",
    "AirSensorParameterStrategy",
    "AirSensorVariableStrategy",
    "HumiditySensorParameters",
    "HumiditySensorVariables",
    "HumiditySensorParameterStrategy",
    "HumiditySensorVariableStrategy",
    "StaticSensorParameters",
    "StaticSensorVariables",
    "StaticSensorParameterStrategy",
    "StaticSensorVariableStrategy",
    "DigitalSensorParameters",
    "DigitalSensorVariables",
    "DigitalSensorParameterStrategy",
    "DigitalSensorVariableStrategy",
    "PositionSensorParameters",
    "PositionSensorVariables",
    "PositionSensorParameterStrategy",
    "PositionSensorVariableStrategy",
    "FeedSensorParameters",
    "FeedSensorVariables",
    "FeedSensorParameterStrategy",
    "FeedSensorVariableStrategy",
    "WaterSensorParameters",
    "WaterSensorVariables",
    "WaterSensorParameterStrategy",
    "WaterSensorVariableStrategy",
    "GasSensorParameters",
    "GasSensorVariables",
    "GasSensorParameterStrategy",
    "GasSensorVariableStrategy",
    # Positional devices
    "InletParameters",
    "InletVariables",
    "InletParameterStrategy",
    "InletVariableStrategy",
    "CurtainParameters",
    "CurtainVariables",
    "CurtainParameterStrategy",
    "CurtainVariableStrategy",
    "RidgeVentParameters",
    "RidgeVentVariables",
    "RidgeVentParameterStrategy",
    "RidgeVentVariableStrategy",
    "ChimneyParameters",
    "ChimneyVariables",
    "ChimneyParameterStrategy",
    "ChimneyVariableStrategy",
    # Climate control
    "HeaterParameters",
    "HeaterVariables",
    "HeaterParameterStrategy",
    "HeaterVariableStrategy",
    "CoolPadParameters",
    "CoolPadVariables",
    "CoolPadParameterStrategy",
    "CoolPadVariableStrategy",
    "FanParameters",
    "FanVariables",
    "FanParameterStrategy",
    "FanVariableStrategy",
    "VariableHeaterParameters",
    "VariableHeaterVariables",
    "VariableHeaterParameterStrategy",
    "VariableHeaterVariableStrategy",
    "VfdFanParameters",
    "VfdFanVariables",
    "VfdFanParameterStrategy",
    "VfdFanVariableStrategy",
    # Other devices
    "TimedParameters",
    "TimedVariables",
    "TimedParameterStrategy",
    "TimedVariableStrategy",
    "SwitchParameters",
    "SwitchVariables",
    "SwitchParameterStrategy",
    "SwitchVariableStrategy",
    "V10LightsParameters",
    "V10LightsVariables",
    "V10LightsParameterStrategy",
    "V10LightsVariableStrategy",
    # Registration
    "register_all_strategies",
]


def register_all_strategies(registry: "DeviceParserRegistry") -> None:
    """
    Register all built-in device strategies with a registry.

    Registers 20 device types covering sensors, positional devices,
    climate control, and other equipment types.

    Args:
        registry: The DeviceParserRegistry to populate.
    """
    # Sensors
    registry.register_parameter_strategy(AirSensorParameterStrategy())
    registry.register_variable_strategy(AirSensorVariableStrategy())

    registry.register_parameter_strategy(HumiditySensorParameterStrategy())
    registry.register_variable_strategy(HumiditySensorVariableStrategy())

    registry.register_parameter_strategy(StaticSensorParameterStrategy())
    registry.register_variable_strategy(StaticSensorVariableStrategy())

    registry.register_parameter_strategy(DigitalSensorParameterStrategy())
    registry.register_variable_strategy(DigitalSensorVariableStrategy())

    registry.register_parameter_strategy(PositionSensorParameterStrategy())
    registry.register_variable_strategy(PositionSensorVariableStrategy())

    registry.register_parameter_strategy(FeedSensorParameterStrategy())
    registry.register_variable_strategy(FeedSensorVariableStrategy())

    registry.register_parameter_strategy(WaterSensorParameterStrategy())
    registry.register_variable_strategy(WaterSensorVariableStrategy())

    registry.register_parameter_strategy(GasSensorParameterStrategy())
    registry.register_variable_strategy(GasSensorVariableStrategy())

    # Positional devices
    registry.register_parameter_strategy(InletParameterStrategy())
    registry.register_variable_strategy(InletVariableStrategy())

    registry.register_parameter_strategy(CurtainParameterStrategy())
    registry.register_variable_strategy(CurtainVariableStrategy())

    registry.register_parameter_strategy(RidgeVentParameterStrategy())
    registry.register_variable_strategy(RidgeVentVariableStrategy())

    registry.register_parameter_strategy(ChimneyParameterStrategy())
    registry.register_variable_strategy(ChimneyVariableStrategy())

    # Climate control
    registry.register_parameter_strategy(HeaterParameterStrategy())
    registry.register_variable_strategy(HeaterVariableStrategy())

    registry.register_parameter_strategy(CoolPadParameterStrategy())
    registry.register_variable_strategy(CoolPadVariableStrategy())

    registry.register_parameter_strategy(FanParameterStrategy())
    registry.register_variable_strategy(FanVariableStrategy())

    registry.register_parameter_strategy(VariableHeaterParameterStrategy())
    registry.register_variable_strategy(VariableHeaterVariableStrategy())

    registry.register_parameter_strategy(VfdFanParameterStrategy())
    registry.register_variable_strategy(VfdFanVariableStrategy())

    # Other devices
    registry.register_parameter_strategy(TimedParameterStrategy())
    registry.register_variable_strategy(TimedVariableStrategy())

    registry.register_parameter_strategy(SwitchParameterStrategy())
    registry.register_variable_strategy(SwitchVariableStrategy())

    registry.register_parameter_strategy(V10LightsParameterStrategy())
    registry.register_variable_strategy(V10LightsVariableStrategy())
