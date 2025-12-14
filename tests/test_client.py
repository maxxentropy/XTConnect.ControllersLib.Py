"""Tests for ControllerClient."""

import pytest

from xtconnect import ControllerClient, ClientState
from xtconnect.exceptions import ConnectionError, TimeoutError
from xtconnect.protocol.constants import CommandCode
from xtconnect.transport.mock import MockTransport


class TestControllerClient:
    """Tests for ControllerClient class."""

    @pytest.fixture
    def mock_transport(self):
        """Create a MockTransport instance."""
        return MockTransport()

    @pytest.fixture
    def client(self, mock_transport):
        """Create a ControllerClient with mock transport."""
        return ControllerClient(mock_transport, timeout=1.0, max_retries=2)

    def test_initial_state(self, client):
        """Test client starts in disconnected state."""
        assert client.state == ClientState.DISCONNECTED
        assert client.serial_number is None
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_connect_success(self, client, mock_transport):
        """Test successful connection."""
        # Queue SN_ACK response
        mock_transport.add_response(bytes([CommandCode.PCMI_SN_ACK]))

        result = await client.connect("00009001")

        assert result is True
        assert client.state == ClientState.CONNECTED
        assert client.serial_number == "00009001"
        assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_timeout_with_retry(self, mock_transport):
        """Test connection retries on timeout."""
        client = ControllerClient(mock_transport, timeout=0.1, max_retries=2)

        # No response queued - will timeout
        with pytest.raises(TimeoutError):
            await client.connect("00009001")

        # Should have tried 3 times (initial + 2 retries)
        assert len(mock_transport.written_data) == 3
        assert client.state == ClientState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_connect_already_connected_raises(self, client, mock_transport):
        """Test that connecting when already connected raises error."""
        mock_transport.add_response(bytes([CommandCode.PCMI_SN_ACK]))
        await client.connect("00009001")

        with pytest.raises(ConnectionError) as exc_info:
            await client.connect("00009002")
        assert "CONNECTED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect(self, client, mock_transport):
        """Test disconnection."""
        # Connect first
        mock_transport.add_response(bytes([CommandCode.PCMI_SN_ACK]))
        await client.connect("00009001")

        # Queue BR_ACK for disconnect
        mock_transport.add_response(bytes([CommandCode.PCMI_BR_ACK]))
        await client.disconnect()

        assert client.state == ClientState.DISCONNECTED
        assert client.serial_number is None

    @pytest.mark.asyncio
    async def test_disconnect_when_disconnected_is_noop(self, client):
        """Test that disconnect when not connected does nothing."""
        await client.disconnect()  # Should not raise
        assert client.state == ClientState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_transport):
        """Test async context manager protocol."""
        mock_transport.add_response(bytes([CommandCode.PCMI_SN_ACK]))
        mock_transport.add_response(bytes([CommandCode.PCMI_BR_ACK]))

        async with ControllerClient(mock_transport) as client:
            await client.connect("00009001")
            assert client.is_connected

        assert not client.is_connected
        assert not mock_transport.is_open

    @pytest.mark.asyncio
    async def test_transport_property(self, client, mock_transport):
        """Test transport property returns the transport."""
        assert client.transport is mock_transport

    @pytest.mark.asyncio
    async def test_repr(self, client, mock_transport):
        """Test string representation."""
        assert "DISCONNECTED" in repr(client)
        assert "None" in repr(client)

        mock_transport.add_response(bytes([CommandCode.PCMI_SN_ACK]))
        await client.connect("00009001")

        assert "CONNECTED" in repr(client)
        assert "00009001" in repr(client)


class TestClientValidation:
    """Tests for client input validation."""

    @pytest.mark.asyncio
    async def test_invalid_serial_number_raises(self):
        """Test that invalid serial number raises validation error."""
        transport = MockTransport()
        client = ControllerClient(transport)

        with pytest.raises(ValueError):
            await client.connect("123")  # Too short

        with pytest.raises(ValueError):
            await client.connect("ABCD1234")  # Non-numeric
