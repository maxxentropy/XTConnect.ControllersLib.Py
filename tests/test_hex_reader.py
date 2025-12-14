"""Tests for HexStringReader."""

import pytest

from xtconnect.parsers.hex_reader import HexStringReader
from xtconnect.protocol.endianness import NON_SWAP_STRATEGY, SWAP_STRATEGY


class TestHexStringReader:
    """Tests for HexStringReader class."""

    def test_read_byte(self):
        """Test reading a single byte."""
        reader = HexStringReader("FF00AB", NON_SWAP_STRATEGY)
        assert reader.read_byte() == 0xFF
        assert reader.read_byte() == 0x00
        assert reader.read_byte() == 0xAB

    def test_read_uint16_non_swap(self):
        """Test reading uint16 in little-endian mode."""
        reader = HexStringReader("3412", NON_SWAP_STRATEGY)
        # Little-endian: 0x34 is low byte, 0x12 is high byte
        assert reader.read_uint16() == 0x1234

    def test_read_uint16_swap(self):
        """Test reading uint16 in big-endian mode."""
        reader = HexStringReader("1234", SWAP_STRATEGY)
        # Big-endian: 0x12 is high byte, 0x34 is low byte
        assert reader.read_uint16() == 0x1234

    def test_read_int16_positive(self):
        """Test reading positive int16."""
        reader = HexStringReader("E803", NON_SWAP_STRATEGY)
        # Little-endian: 0x03E8 = 1000
        assert reader.read_int16() == 1000

    def test_read_int16_negative(self):
        """Test reading negative int16."""
        reader = HexStringReader("18FC", NON_SWAP_STRATEGY)
        # Little-endian: 0xFC18 = -1000 (two's complement)
        assert reader.read_int16() == -1000

    def test_read_uint32_non_swap(self):
        """Test reading uint32 in little-endian mode."""
        reader = HexStringReader("78563412", NON_SWAP_STRATEGY)
        assert reader.read_uint32() == 0x12345678

    def test_read_uint32_swap(self):
        """Test reading uint32 in big-endian mode."""
        reader = HexStringReader("12345678", SWAP_STRATEGY)
        assert reader.read_uint32() == 0x12345678

    def test_skip_bytes(self):
        """Test skipping bytes."""
        reader = HexStringReader("00112233", NON_SWAP_STRATEGY)
        reader.skip_bytes(2)
        assert reader.read_byte() == 0x22
        assert reader.read_byte() == 0x33

    def test_remaining_property(self):
        """Test remaining hex chars property."""
        reader = HexStringReader("00112233", NON_SWAP_STRATEGY)
        assert reader.remaining == 8
        reader.read_byte()
        assert reader.remaining == 6

    def test_position_property(self):
        """Test position property."""
        reader = HexStringReader("00112233", NON_SWAP_STRATEGY)
        assert reader.position == 0
        reader.read_byte()
        assert reader.position == 2

    def test_peek_byte(self):
        """Test peeking at next byte without consuming."""
        reader = HexStringReader("AABB", NON_SWAP_STRATEGY)
        assert reader.peek_byte() == 0xAA
        assert reader.peek_byte() == 0xAA  # Still the same
        assert reader.read_byte() == 0xAA  # Now consume
        assert reader.peek_byte() == 0xBB

    def test_slice(self):
        """Test reading raw hex substring using slice."""
        reader = HexStringReader("001122334455", NON_SWAP_STRATEGY)
        assert reader.slice(2) == "0011"  # 2 bytes = 4 hex chars
        assert reader.slice(2) == "2233"

    def test_empty_reader(self):
        """Test empty reader behavior."""
        from xtconnect.exceptions import ParseError

        reader = HexStringReader("", NON_SWAP_STRATEGY)
        assert reader.remaining == 0
        with pytest.raises(ParseError):
            reader.read_byte()

    def test_insufficient_data(self):
        """Test reading more data than available."""
        from xtconnect.exceptions import ParseError

        reader = HexStringReader("00", NON_SWAP_STRATEGY)
        reader.read_byte()
        with pytest.raises(ParseError):
            reader.read_byte()

    def test_lowercase_hex(self):
        """Test reading lowercase hex characters."""
        reader = HexStringReader("abcdef", NON_SWAP_STRATEGY)
        assert reader.read_byte() == 0xAB
        assert reader.read_byte() == 0xCD
        assert reader.read_byte() == 0xEF
