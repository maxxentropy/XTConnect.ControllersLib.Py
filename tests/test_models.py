"""Tests for data models."""

import pytest

from xtconnect.models.records import (
    DeviceRecordHeader,
    DeviceType,
    SerialNumber,
    Temperature,
    VersionRecord,
)


class TestTemperature:
    """Tests for Temperature model."""

    def test_from_raw_value_positive(self):
        """Test creating temperature from positive raw value."""
        temp = Temperature(raw_value=720)  # 72.0F
        assert temp.raw_value == 720
        assert temp.fahrenheit == 72.0

    def test_from_raw_value_negative(self):
        """Test creating temperature from negative raw value."""
        temp = Temperature(raw_value=-100)  # -10.0F
        assert temp.raw_value == -100
        assert temp.fahrenheit == -10.0

    def test_celsius_conversion(self):
        """Test Fahrenheit to Celsius conversion."""
        temp = Temperature(raw_value=320)  # 32.0F = 0.0C
        assert temp.celsius == pytest.approx(0.0, abs=0.01)

        temp = Temperature(raw_value=2120)  # 212.0F = 100.0C
        assert temp.celsius == pytest.approx(100.0, abs=0.01)

    def test_from_fahrenheit(self):
        """Test creating temperature from Fahrenheit value."""
        temp = Temperature.from_fahrenheit(72.5)
        assert temp.fahrenheit == 72.5
        assert temp.raw_value == 725

    def test_is_valid(self):
        """Test validity check for normal values."""
        temp = Temperature(raw_value=720)
        assert temp.is_valid is True

    def test_is_valid_invalid_marker(self):
        """Test validity check for invalid marker value."""
        temp = Temperature(raw_value=0x7FFF)  # Invalid marker
        assert temp.is_valid is False

    def test_equality(self):
        """Test temperature equality."""
        temp1 = Temperature(raw_value=720)
        temp2 = Temperature(raw_value=720)
        temp3 = Temperature(raw_value=730)
        assert temp1 == temp2
        assert temp1 != temp3

    def test_repr(self):
        """Test string representation."""
        temp = Temperature(raw_value=720)
        assert "72.0" in repr(temp)


class TestSerialNumber:
    """Tests for SerialNumber validation."""

    def test_valid_serial_number(self):
        """Test valid 8-digit serial number."""
        sn = SerialNumber(value="00009001")
        assert sn.value == "00009001"

    def test_serial_number_rejects_whitespace(self):
        """Test that serial number with extra whitespace is rejected."""
        # Serial number must be exactly 8 characters
        with pytest.raises(ValueError):
            SerialNumber(value="  00009001  ")

    def test_invalid_length_raises(self):
        """Test that wrong length raises error."""
        with pytest.raises(ValueError):
            SerialNumber(value="123")

    def test_non_numeric_raises(self):
        """Test that non-numeric characters raise error."""
        with pytest.raises(ValueError):
            SerialNumber(value="0000ABCD")


class TestDeviceType:
    """Tests for DeviceType enum."""

    def test_air_sensor(self):
        """Test AIR_SENSOR device type."""
        assert DeviceType.AIR_SENSOR.value == 1

    def test_fan(self):
        """Test FAN device type."""
        assert DeviceType.FAN.value == 8

    def test_heater(self):
        """Test HEATER device type."""
        assert DeviceType.HEATER.value == 6

    def test_inlet(self):
        """Test INLET device type."""
        assert DeviceType.INLET.value == 3

    def test_unknown(self):
        """Test UNKNOWN device type."""
        assert DeviceType.UNKNOWN.value == 0


class TestDeviceRecordHeader:
    """Tests for DeviceRecordHeader model."""

    def test_header_creation(self):
        """Test creating device record header."""
        header = DeviceRecordHeader(
            record_size_words=16,
            zone_number=1,
            record_type=0,
            record_format=2,
            device_type=DeviceType.FAN,
            device_subtype=0,
            module_address=1,
            channel_number=0,
        )
        assert header.zone_number == 1
        assert header.device_type == DeviceType.FAN
        assert header.record_size_words == 16

    def test_header_record_format(self):
        """Test record format field."""
        header = DeviceRecordHeader(
            record_size_words=16,
            zone_number=1,
            record_type=0,
            record_format=1,  # < 20 = swap (big-endian)
            device_type=DeviceType.FAN,
            device_subtype=0,
            module_address=1,
            channel_number=0,
        )
        assert header.record_format == 1

        header2 = DeviceRecordHeader(
            record_size_words=16,
            zone_number=1,
            record_type=0,
            record_format=20,  # >= 20 = non-swap (little-endian)
            device_type=DeviceType.FAN,
            device_subtype=0,
            module_address=1,
            channel_number=0,
        )
        assert header2.record_format == 20


class TestVersionRecord:
    """Tests for VersionRecord model."""

    def test_version_record_creation(self):
        """Test creating version record."""
        version = VersionRecord(
            version_string="XT3000 v2.1",
            date_code="20231015",
            raw_data="",
        )
        assert version.version_string == "XT3000 v2.1"
        assert version.date_code == "20231015"
