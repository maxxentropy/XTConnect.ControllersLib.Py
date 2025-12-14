"""Tests for checksum functions."""

import pytest

from xtconnect.protocol.checksums import (
    append_checksum,
    calculate_checksum,
    validate_checksum,
)


class TestChecksums:
    """Tests for checksum calculation and validation."""

    def test_calculate_checksum_basic(self):
        """Test basic checksum calculation."""
        # Sum of all bytes, mod 256
        data = bytes([0x82, 0x08, 0x30, 0x30, 0x30, 0x30, 0x39, 0x30, 0x30, 0x31])
        checksum = calculate_checksum(data)
        assert isinstance(checksum, int)
        assert 0 <= checksum <= 255

    def test_calculate_checksum_single_byte(self):
        """Test checksum of single byte."""
        data = bytes([0x42])
        assert calculate_checksum(data) == 0x42

    def test_calculate_checksum_two_bytes(self):
        """Test checksum of two bytes."""
        data = bytes([0xFF, 0xFF])
        # 0xFF + 0xFF = 0x1FE & 0xFF = 0xFE (254)
        assert calculate_checksum(data) == 0xFE

    def test_calculate_checksum_empty(self):
        """Test checksum of empty data."""
        data = b""
        assert calculate_checksum(data) == 0x00

    def test_append_checksum(self):
        """Test appending checksum to data."""
        data = bytes([0x82])
        result = append_checksum(data)
        # Should have original data + 2 hex chars for checksum
        assert result.startswith(data)
        assert len(result) == len(data) + 2

    def test_append_checksum_format(self):
        """Test that appended checksum is uppercase hex."""
        data = bytes([0x0F])  # Sum = 0x0F
        result = append_checksum(data)
        # Checksum should be "0F" (uppercase, zero-padded)
        assert result[-2:] == b"0F"

    def test_validate_checksum_valid(self):
        """Test validation of correct checksum."""
        data = bytes([0x82])
        with_checksum = append_checksum(data)
        # validate_checksum requires checksum_offset parameter
        assert validate_checksum(with_checksum, 1) is True

    def test_validate_checksum_invalid(self):
        """Test validation of incorrect checksum."""
        # Data with wrong checksum
        data = bytes([0x82]) + b"00"  # Wrong checksum
        assert validate_checksum(data, 1) is False

    def test_validate_checksum_too_short(self):
        """Test validation of data too short for checksum."""
        data = b"A"  # Only 1 byte, need at least 3 (1 data + 2 checksum)
        # With offset 0, needs 2 more chars for checksum
        assert validate_checksum(data, 0) is False

    def test_checksum_roundtrip(self):
        """Test that append and validate work together."""
        original = b"Hello World"
        with_checksum = append_checksum(original)
        assert validate_checksum(with_checksum, len(original)) is True

    def test_checksum_with_ascii_data(self):
        """Test checksum with ASCII hex-encoded data."""
        # Simulating protocol frame content
        data = b"\x82" + b"00009001"  # Command + serial number
        with_checksum = append_checksum(data)
        assert validate_checksum(with_checksum, len(data)) is True
