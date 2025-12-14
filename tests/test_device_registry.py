"""Tests for device parser registry."""

import pytest

from xtconnect.models.records import DeviceRecordHeader, DeviceType
from xtconnect.parsers.device_registry import (
    DeviceParserRegistry,
    GenericDeviceParameters,
    GenericDeviceVariables,
    create_default_registry,
)


class TestDeviceParserRegistry:
    """Tests for DeviceParserRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create an empty registry."""
        return DeviceParserRegistry()

    def test_empty_registry(self, registry):
        """Test empty registry behavior."""
        assert registry.get_parameter_strategy(DeviceType.FAN) is None
        assert registry.get_variable_strategy(DeviceType.FAN) is None
        assert not registry.has_parameter_strategy(DeviceType.FAN)
        assert not registry.has_variable_strategy(DeviceType.FAN)

    def test_registered_types_empty(self, registry):
        """Test registered types on empty registry."""
        assert registry.registered_parameter_types == frozenset()
        assert registry.registered_variable_types == frozenset()

    def test_clear_registry(self, registry):
        """Test clearing registry."""
        # Create default registry with strategies
        registry = create_default_registry()
        assert len(registry.registered_parameter_types) > 0

        registry.clear()
        assert len(registry.registered_parameter_types) == 0
        assert len(registry.registered_variable_types) == 0

    def test_unregister_strategy(self, registry):
        """Test unregistering strategies."""
        registry = create_default_registry()

        result = registry.unregister_parameter_strategy(DeviceType.FAN)
        assert result is True
        assert not registry.has_parameter_strategy(DeviceType.FAN)

        # Unregistering non-existent returns False
        result = registry.unregister_parameter_strategy(DeviceType.FAN)
        assert result is False

    def test_repr(self, registry):
        """Test string representation."""
        assert "params=0" in repr(registry)
        assert "vars=0" in repr(registry)


class TestCreateDefaultRegistry:
    """Tests for create_default_registry function."""

    def test_creates_populated_registry(self):
        """Test that default registry has all device types."""
        registry = create_default_registry()

        # Should have 20 device types registered
        assert len(registry.registered_parameter_types) == 20
        assert len(registry.registered_variable_types) == 20

    def test_has_sensor_strategies(self):
        """Test that sensor strategies are registered."""
        registry = create_default_registry()

        assert registry.has_parameter_strategy(DeviceType.AIR_SENSOR)
        assert registry.has_variable_strategy(DeviceType.AIR_SENSOR)
        assert registry.has_parameter_strategy(DeviceType.HUMIDITY_SENSOR)
        assert registry.has_variable_strategy(DeviceType.HUMIDITY_SENSOR)

    def test_has_climate_strategies(self):
        """Test that climate control strategies are registered."""
        registry = create_default_registry()

        assert registry.has_parameter_strategy(DeviceType.FAN)
        assert registry.has_variable_strategy(DeviceType.FAN)
        assert registry.has_parameter_strategy(DeviceType.HEATER)
        assert registry.has_variable_strategy(DeviceType.HEATER)
        assert registry.has_parameter_strategy(DeviceType.COOLPAD)
        assert registry.has_variable_strategy(DeviceType.COOLPAD)

    def test_has_positional_strategies(self):
        """Test that positional device strategies are registered."""
        registry = create_default_registry()

        assert registry.has_parameter_strategy(DeviceType.INLET)
        assert registry.has_variable_strategy(DeviceType.INLET)
        assert registry.has_parameter_strategy(DeviceType.CURTAIN)
        assert registry.has_variable_strategy(DeviceType.CURTAIN)

    def test_creates_new_instance_each_call(self):
        """Test that each call creates a new registry instance."""
        registry1 = create_default_registry()
        registry2 = create_default_registry()

        assert registry1 is not registry2


class TestGenericDeviceData:
    """Tests for generic device data classes."""

    @pytest.fixture
    def header(self):
        """Create a sample device record header."""
        return DeviceRecordHeader(
            record_size_words=16,
            zone_number=1,
            record_type=0,
            record_format=2,
            device_type=DeviceType.FAN,
            device_subtype=0,
            module_address=1,
            channel_number=0,
        )

    def test_generic_device_parameters(self, header):
        """Test GenericDeviceParameters class."""
        params = GenericDeviceParameters(
            header=header,
            raw_data="001122334455",
        )
        assert params.device_type == DeviceType.FAN
        assert params.raw_data == "001122334455"

    def test_generic_device_variables(self, header):
        """Test GenericDeviceVariables class."""
        vars_ = GenericDeviceVariables(
            header=header,
            raw_data="AABBCCDD",
        )
        assert vars_.device_type == DeviceType.FAN
        assert vars_.raw_data == "AABBCCDD"
