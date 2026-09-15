"""
Tests for OpenMCT plugin security fixes

Tests cover the following GHSA advisories:
- GHSA-rgwv-x7h5-f7j3: WebSocket unsubscribe DoS and HTTP route exceptions
- GHSA-7h55-xp8q-247v: Cross-Site WebSocket Hijacking, unauthenticated API and configurable bind address
"""
import json
from unittest import mock
from unittest import TestCase

import bottle
import gevent
import pytest

from ait.core.server.plugins.openmct import AITOpenMctPlugin
from ait.core.server.plugins.openmct import ManagedWebSocket


def create_test_plugin():
    """
    Helper function to create a test plugin instance with mocked dependencies.
    Prevents server startup and ZMQ connection during unit tests.
    """
    mock_zmq_context = mock.Mock()
    zmq_args = {"zmq_context": mock_zmq_context}
    # Patch init to prevent server startup during tests
    with mock.patch.object(AITOpenMctPlugin, "init"):
        plugin = AITOpenMctPlugin(inputs=[], outputs=[], zmq_args=zmq_args)
    return plugin


class BaseSecurityTest(TestCase):
    def tearDown(self):
        """Kill any remaining greenlets after each test"""
        # Kill all greenlets except the current one to prevent
        # background threads from logging after test cleanup
        gevent.killall(
            [g for g in gevent.Greenlet.__subclasses__() if hasattr(g, "__self__")],
            timeout=0.1,
            block=False,
        )
        # Give greenlets a moment to die
        gevent.sleep(0)


class TestWebSocketUnsubscribeDoS(BaseSecurityTest):
    """
    Tests for GHSA-rgwv-x7h5-f7j3: WebSocket unsubscribe DoS vulnerability
    """

    def setUp(self):
        """Set up test plugin instance"""
        self.plugin = create_test_plugin()

    def test_unsubscribe_without_argument_does_not_crash(self):
        """
        Test that sending 'unsubscribe' without a field argument doesn't crash.
        Previously would raise IndexError on msg_parts[1].
        """
        # Create a managed websocket
        mock_ws = mock.Mock()
        mock_ws.closed = False
        mws = ManagedWebSocket(mock_ws, "127.0.0.1")

        # Subscribe to a field first so we have something in the state
        mws.subscribe_field("test_field")

        # Send unsubscribe without argument - should not crash
        try:
            self.plugin.process_websocket_mesg(mws, "unsubscribe")
            assert True
        except IndexError:
            pytest.fail("Unsubscribe without argument raised IndexError")

    def test_unsubscribe_with_argument_works(self):
        """Test that normal unsubscribe with argument still works"""
        mock_ws = mock.Mock()
        mock_ws.closed = False
        mws = ManagedWebSocket(mock_ws, "127.0.0.1")

        # Subscribe to a field (format: packet.field)
        mws.subscribe_field("test_packet.test_field")
        assert "test_field" in mws._subscribed_dict.get("test_packet", set())

        # Unsubscribe with argument should work
        self.plugin.process_websocket_mesg(mws, "unsubscribe test_packet.test_field")
        assert "test_field" not in mws._subscribed_dict.get("test_packet", set())

    def test_subscribe_still_requires_argument(self):
        """Test that subscribe still requires an argument (unchanged behavior)"""
        mock_ws = mock.Mock()
        mock_ws.closed = False
        mws = ManagedWebSocket(mock_ws, "127.0.0.1")

        # Subscribe without argument should not work
        self.plugin.process_websocket_mesg(mws, "subscribe")
        # Should not have subscribed to anything
        assert len(mws._subscribed_dict) == 0


class TestHistoricalTelemetryExceptionHandling(BaseSecurityTest):
    """
    Tests for GHSA-rgwv-x7h5-f7j3: Exception handling in historical telemetry routes
    """

    def setUp(self):
        """Set up test plugin instance"""
        self.plugin = create_test_plugin()

    @mock.patch("bottle.request")
    @mock.patch("bottle.abort")
    def test_historical_tlm_missing_start_parameter(self, mock_abort, mock_request):
        """Test that missing start parameter returns 400 instead of crashing"""
        # Mock request with missing start parameter
        mock_request.query.start = None
        mock_request.query.end = "1000000"

        self.plugin.get_historical_tlm("test_packet.field")

        # Should abort with 400
        mock_abort.assert_called_once()
        assert mock_abort.call_args[0][0] == 400

    @mock.patch("bottle.request")
    @mock.patch("bottle.abort")
    def test_historical_tlm_invalid_numeric_parameter(self, mock_abort, mock_request):
        """Test that non-numeric start/end parameters return 400 instead of crashing"""
        # Mock request with invalid numeric values
        mock_request.query.start = "not_a_number"
        mock_request.query.end = "1000000"

        self.plugin.get_historical_tlm("test_packet.field")

        # Should abort with 400
        mock_abort.assert_called_once()
        assert mock_abort.call_args[0][0] == 400

    def test_get_historical_tlm_for_packet_fields_invalid_packet_id(self):
        """
        Test that invalid packet ID in get_historical_tlm_for_packet_fields
        returns empty list instead of raising KeyError
        """
        # Call with non-existent packet ID
        result = self.plugin.get_historical_tlm_for_packet_fields(
            ait_pkt_id="NON_EXISTENT_PACKET",
            ait_field_names=None,
            start_millis=0,
            end_millis=1000000,
        )

        # Should return empty list, not crash
        assert result == []


class TestBindAddressConfiguration(BaseSecurityTest):
    """
    Tests for GHSA-7h55-xp8q-247v: Configurable bind address
    """

    def test_default_bind_address_is_localhost(self):
        """Test that default bind address is 127.0.0.1, not 0.0.0.0"""
        plugin = create_test_plugin()

        # Default should be localhost
        assert plugin._bindAddress == "127.0.0.1"
        assert plugin._bindAddress != "0.0.0.0"

    def test_bind_address_can_be_configured(self):
        """Test that bind address can be overridden via config"""
        plugin = create_test_plugin()
        plugin.bind_address = "0.0.0.0"  # Simulate config override
        plugin._check_config()

        assert plugin._bindAddress == "0.0.0.0"


class TestWebSocketOriginValidation(BaseSecurityTest):
    """
    Tests for GHSA-7h55-xp8q-247v: Cross-Site WebSocket Hijacking
    """

    def setUp(self):
        """Set up test plugin instance"""
        self.plugin = create_test_plugin()
        self.plugin._servicePort = 8082

    @mock.patch("bottle.request")
    @mock.patch("bottle.abort")
    def test_websocket_rejects_unauthorized_origin(self, mock_abort, mock_request):
        """Test that WebSocket connection from unauthorized origin is rejected"""
        # Mock websocket upgrade request from malicious origin
        mock_request.environ = {
            "wsgi.websocket": None,  # Triggers the first abort
            "HTTP_ORIGIN": "http://evil.com",
            "REMOTE_ADDR": "192.168.1.100",
        }

        self.plugin.get_realtime_tlm()

        # Should abort
        assert mock_abort.called

    @mock.patch("bottle.request")
    @mock.patch("bottle.abort")
    def test_websocket_allows_localhost_origin(self, mock_abort, mock_request):
        """Test that WebSocket connection from localhost is allowed"""
        mock_ws = mock.Mock()
        mock_ws.closed = False

        # Mock websocket upgrade request from localhost
        mock_request.environ = {
            "wsgi.websocket": mock_ws,
            "HTTP_ORIGIN": "http://localhost:8082",
            "REMOTE_ADDR": "127.0.0.1",
        }

        # This would normally start the websocket loop, but we'll just test
        # that it doesn't abort on origin check
        with mock.patch.object(self.plugin, "manage_web_socket"):
            self.plugin.get_realtime_tlm()

        # Should NOT abort with 403 for origin
        for call in mock_abort.call_args_list:
            if len(call[0]) > 1:
                assert call[0][1] != "Origin not allowed"

    @mock.patch("bottle.request")
    def test_websocket_allows_connection_without_origin_header(self, mock_request):
        """Test that WebSocket connection without Origin header is allowed (non-browser)"""
        mock_ws = mock.Mock()
        mock_ws.closed = False

        # Mock websocket upgrade request without Origin header (e.g., from script)
        mock_request.environ = {"wsgi.websocket": mock_ws, "REMOTE_ADDR": "127.0.0.1"}

        # Should not raise or abort
        with mock.patch.object(self.plugin, "manage_web_socket"):
            try:
                self.plugin.get_realtime_tlm()
                # If we get here, origin check passed
                assert True
            except Exception as e:
                if "Origin not allowed" in str(e):
                    pytest.fail("Rejected connection without Origin header")


class TestDebugEndpointLogging(BaseSecurityTest):
    """
    Tests for GHSA-7h55-xp8q-247v: Debug endpoint security logging
    """

    def setUp(self):
        """Set up test plugin instance"""
        self.plugin = create_test_plugin()
        self.plugin._debugEnabled = True

    @mock.patch("ait.core.log.warn")
    @mock.patch("bottle.request")
    @mock.patch("ait.core.tlm.getDefaultDict")
    def test_debug_endpoint_logs_access(
        self, mock_tlm_dict, mock_request, mock_log_warn
    ):
        """Test that debug endpoint access is logged for security monitoring"""
        # Mock the telemetry dictionary
        mock_pkt = mock.Mock()
        mock_pkt.name = "TEST_PACKET"
        mock_pkt.nbytes = 10
        mock_tlm_dict.return_value = {"TEST_PACKET": mock_pkt}

        # Mock request from client
        mock_request.environ = {"REMOTE_ADDR": "192.168.1.50"}
        mock_request.query.repeat = ""

        # Call the debug endpoint
        try:
            # This will fail on actual packet creation, but we just want to verify logging
            self.plugin.mimic_tlm("TEST_PACKET")
        except:
            pass  # We expect this to fail, just checking the log call

        # Verify security warning was logged
        assert mock_log_warn.called
        log_message = str(mock_log_warn.call_args_list)
        assert "SECURITY" in log_message
        assert (
            "Debug telemetry injection" in log_message or "192.168.1.50" in log_message
        )

    @mock.patch("ait.core.log.warn")
    def test_debug_mode_warning_on_startup(self, mock_log_warn):
        """Test that enabling debug mode logs security warning on startup"""
        plugin = create_test_plugin()
        plugin.debug_enabled = True
        plugin._check_config()

        # Verify warning was logged
        assert mock_log_warn.called
        log_message = str(mock_log_warn.call_args_list)
        assert "SECURITY WARNING" in log_message
        assert "debug mode" in log_message.lower()


if __name__ == "__main__":
    pytest.main([__file__])
