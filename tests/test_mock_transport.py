"""Tests for MockTransport."""

import pytest

from xtconnect.exceptions import TimeoutError, TransportError
from xtconnect.transport.mock import MockTransport, ScriptedMockTransport


class TestMockTransport:
    """Tests for MockTransport class."""

    @pytest.fixture
    def transport(self):
        """Create a MockTransport instance."""
        return MockTransport()

    @pytest.mark.asyncio
    async def test_open_close(self, transport):
        """Test opening and closing transport."""
        assert not transport.is_open
        await transport.open()
        assert transport.is_open
        await transport.close()
        assert not transport.is_open

    @pytest.mark.asyncio
    async def test_double_open_raises(self, transport):
        """Test that opening twice raises error."""
        await transport.open()
        with pytest.raises(TransportError):
            await transport.open()

    @pytest.mark.asyncio
    async def test_write_records_data(self, transport):
        """Test that write records data."""
        await transport.open()
        await transport.write(b"hello")
        await transport.write(b"world")
        assert transport.written_data == [b"hello", b"world"]
        assert transport.last_written == b"world"

    @pytest.mark.asyncio
    async def test_write_when_closed_raises(self, transport):
        """Test that writing to closed transport raises."""
        with pytest.raises(TransportError):
            await transport.write(b"test")

    @pytest.mark.asyncio
    async def test_read_byte_from_response(self, transport):
        """Test reading single byte from queued response."""
        await transport.open()
        transport.add_response(bytes([0x86]))
        result = await transport.read_byte()
        assert result == 0x86

    @pytest.mark.asyncio
    async def test_read_byte_no_data_raises(self, transport):
        """Test that reading with no data raises timeout."""
        await transport.open()
        with pytest.raises(TimeoutError):
            await transport.read_byte()

    @pytest.mark.asyncio
    async def test_read_until_terminator(self, transport):
        """Test reading until terminator."""
        await transport.open()
        transport.add_response(b"hello\x0d")
        result = await transport.read_until(0x0D)
        assert result == b"hello\x0d"

    @pytest.mark.asyncio
    async def test_read_exact_bytes(self, transport):
        """Test reading exact number of bytes."""
        await transport.open()
        transport.add_response(b"hello world")
        result = await transport.read(5)
        assert result == b"hello"
        result = await transport.read(6)
        assert result == b" world"

    @pytest.mark.asyncio
    async def test_add_responses_multiple(self, transport):
        """Test adding multiple responses at once."""
        await transport.open()
        transport.add_responses(b"\x86", b"\x87", b"\x88")
        assert await transport.read_byte() == 0x86
        assert await transport.read_byte() == 0x87
        assert await transport.read_byte() == 0x88

    @pytest.mark.asyncio
    async def test_clear(self, transport):
        """Test clearing transport state."""
        await transport.open()
        await transport.write(b"test")
        transport.add_response(b"\x86")
        transport.clear()
        assert transport.written_data == []
        with pytest.raises(TimeoutError):
            await transport.read_byte()

    @pytest.mark.asyncio
    async def test_discard_buffers(self, transport):
        """Test discarding buffers."""
        await transport.open()
        transport.add_response(b"buffered data")
        await transport.read(4)  # Read partial
        transport.discard_buffers()
        with pytest.raises(TimeoutError):
            await transport.read_byte()

    @pytest.mark.asyncio
    async def test_response_callback(self, transport):
        """Test dynamic response callback."""
        await transport.open()

        def echo_callback(data: bytes) -> bytes | None:
            return data  # Echo back what was written

        transport.set_response_callback(echo_callback)
        await transport.write(b"\x86")
        result = await transport.read_byte()
        assert result == 0x86

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager protocol."""
        async with MockTransport() as transport:
            assert transport.is_open
            transport.add_response(b"\x86")
            assert await transport.read_byte() == 0x86
        assert not transport.is_open

    def test_assert_written(self, transport):
        """Test assert_written helper."""
        import asyncio

        async def run():
            await transport.open()
            await transport.write(b"test")
            transport.assert_written(b"test")
            transport.assert_written(b"test", 0)
            transport.assert_written(b"test", -1)

        asyncio.run(run())

    def test_assert_written_fails(self, transport):
        """Test assert_written raises on mismatch."""
        import asyncio

        async def run():
            await transport.open()
            await transport.write(b"test")
            with pytest.raises(AssertionError):
                transport.assert_written(b"wrong")

        asyncio.run(run())

    def test_assert_write_count(self, transport):
        """Test assert_write_count helper."""
        import asyncio

        async def run():
            await transport.open()
            await transport.write(b"a")
            await transport.write(b"b")
            transport.assert_write_count(2)
            with pytest.raises(AssertionError):
                transport.assert_write_count(3)

        asyncio.run(run())


class TestScriptedMockTransport:
    """Tests for ScriptedMockTransport class."""

    @pytest.fixture
    def transport(self):
        """Create a ScriptedMockTransport instance."""
        return ScriptedMockTransport()

    @pytest.mark.asyncio
    async def test_scripted_responses(self, transport):
        """Test scripted request/response pairs."""
        await transport.open()
        transport.expect(response=b"\x86", request=b"request1")
        transport.expect(response=b"\x87", request=b"request2")

        await transport.write(b"request1")
        assert await transport.read_byte() == 0x86

        await transport.write(b"request2")
        assert await transport.read_byte() == 0x87

    @pytest.mark.asyncio
    async def test_scripted_any_request(self, transport):
        """Test scripted response for any request."""
        await transport.open()
        transport.expect(response=b"\x86")  # No specific request

        await transport.write(b"anything")
        assert await transport.read_byte() == 0x86

    @pytest.mark.asyncio
    async def test_scripted_wrong_request_raises(self, transport):
        """Test that wrong request raises assertion."""
        await transport.open()
        transport.expect(response=b"\x86", request=b"expected")

        with pytest.raises(AssertionError) as exc_info:
            await transport.write(b"wrong")
        assert "Script mismatch" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reset_script(self, transport):
        """Test resetting script to beginning."""
        await transport.open()
        transport.expect(response=b"\x86")
        transport.expect(response=b"\x87")

        await transport.write(b"a")
        await transport.read_byte()

        transport.reset_script()

        await transport.write(b"b")
        assert await transport.read_byte() == 0x86  # Back to first response
