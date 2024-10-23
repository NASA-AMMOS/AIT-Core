from unittest import mock

import gevent
import pytest
import zmq.green

from ait.core.server.broker import Broker
from ait.core.server.handlers import PacketHandler
from ait.core.server.stream import input_stream_factory
from ait.core.server.stream import output_stream_factory
from ait.core.server.stream import PortOutputStream
from ait.core.server.stream import TCPInputClientStream
from ait.core.server.stream import TCPInputServerStream
from ait.core.server.stream import UDPInputServerStream
from ait.core.server.stream import ZMQStream


broker = Broker()


class TestStream:
    invalid_stream_args = [
        "some_stream",
        "input_stream",
        [
            PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER"),
            PacketHandler(input_type=int, packet="CCSDS_HEADER"),
        ],
        {"zmq_context": broker},
    ]
    test_data = [
        (
            "zmq",
            {
                "name": "some_zmq_stream",
                "inputs": ["input_stream"],
                "handlers_len": 1,
                "handler_type": PacketHandler,
                "broker_context": broker.context,
                "sub_type": zmq.green.core._Socket,
                "pub_type": zmq.green.core._Socket,
                "repr": "<ZMQStream name=some_zmq_stream>",
            },
        ),
        (
            "udp_server",
            {
                "name": "some_udp_stream",
                "inputs": [1234],
                "handlers_len": 1,
                "handler_type": PacketHandler,
                "broker_context": broker.context,
                "sub_type": gevent._socket3.socket,
                "pub_type": zmq.green.core._Socket,
                "repr": "<UDPInputServerStream name=some_udp_stream>",
            },
        ),
        (
            "tcp_server",
            {
                "name": "some_tcp_stream_server",
                "inputs": ["server", 1234],
                "handlers_len": 1,
                "handler_type": PacketHandler,
                "broker_context": broker.context,
                "sub_type": gevent._socket3.socket,
                "pub_type": zmq.green.core._Socket,
                "repr": "<TCPInputServerStream name=some_tcp_stream_server>",
            },
        ),
        (
            "tcp_client",
            {
                "name": "some_tcp_stream_client",
                "inputs": ["127.0.0.1", 1234],
                "handlers_len": 1,
                "handler_type": PacketHandler,
                "broker_context": broker.context,
                "sub_type": gevent._socket3.socket,
                "pub_type": zmq.green.core._Socket,
                "repr": "<TCPInputClientStream name=some_tcp_stream_client>",
            },
        ),
    ]

    def setup_method(self):
        self.streams = {
            "zmq": ZMQStream(
                "some_zmq_stream",
                ["input_stream"],
                [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
                zmq_args={"zmq_context": broker.context},
            ),
            "udp_server": UDPInputServerStream(
                "some_udp_stream",
                [1234],
                [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
                zmq_args={"zmq_context": broker.context},
            ),
            "tcp_server": TCPInputServerStream(
                "some_tcp_stream_server",
                ["server", 1234],
                [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
                zmq_args={"zmq_context": broker.context},
            ),
            "tcp_client": TCPInputClientStream(
                "some_tcp_stream_client",
                ["127.0.0.1", 1234],
                [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
                zmq_args={"zmq_context": broker.context},
            ),
        }
        for stream in self.streams.values():
            stream.handlers = [
                PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")
            ]

    @pytest.mark.parametrize("stream,expected", test_data)
    def test_stream_creation(self, stream, expected):
        assert self.streams[stream].name is expected["name"]
        assert self.streams[stream].inputs == expected["inputs"]
        assert len(self.streams[stream].handlers) == expected["handlers_len"]
        assert type(self.streams[stream].handlers[0]) == expected["handler_type"]
        assert self.streams[stream].context == expected["broker_context"]
        assert type(self.streams[stream].pub) == expected["pub_type"]
        assert type(self.streams[stream].sub) == expected["sub_type"]

    @pytest.mark.parametrize("stream,expected", test_data)
    def test_repr(self, stream, expected):
        assert self.streams[stream].__repr__() == expected["repr"]

    @pytest.mark.parametrize("stream,_", test_data)
    @mock.patch.object(PacketHandler, "handle")
    def test_process(self, execute_handler_mock, stream, _):
        self.streams[stream].process("input_data")
        execute_handler_mock.assert_called_with("input_data")

    @pytest.mark.parametrize("stream,_", test_data)
    def test_valid_workflow_one_handler(self, stream, _):
        assert self.streams[stream].valid_workflow() is True

    @pytest.mark.parametrize("stream,_", test_data)
    def test_valid_workflow_more_handlers(self, stream, _):
        self.streams[stream].handlers.append(
            PacketHandler(input_type=str, packet="CCSDS_HEADER")
        )
        assert self.streams[stream].valid_workflow() is True

    @pytest.mark.parametrize("stream,_", test_data)
    def test_invalid_workflow_more_handlers(self, stream, _):
        self.streams[stream].handlers.append(
            PacketHandler(input_type=int, packet="CCSDS_HEADER")
        )
        assert self.streams[stream].valid_workflow() is False

    @pytest.mark.parametrize(
        "stream,args",
        [
            (ZMQStream, invalid_stream_args),
            (UDPInputServerStream, invalid_stream_args),
            (TCPInputServerStream, invalid_stream_args),
            (TCPInputClientStream, invalid_stream_args),
        ],
    )
    def test_stream_creation_invalid_workflow(self, stream, args):
        with pytest.raises(ValueError):
            stream(*args)

    @pytest.mark.parametrize(
        "args,expected",
        [
            (["TCP", "127.0.0.1", 1234], TCPInputServerStream),
            (["TCP", "server", 1234], TCPInputServerStream),
            (["TCP", "0.0.0.0", 1234], TCPInputServerStream),
            (["TCP", "localhost", 1234], TCPInputServerStream),
            (["TCP", "foo", 1234], TCPInputClientStream),
            ([1234], UDPInputServerStream),
            (1234, UDPInputServerStream),
            (["UDP", "server", 1234], UDPInputServerStream),
            (["UDP", "localhost", 1234], UDPInputServerStream),
            (["UDP", "0.0.0.0", 1234], UDPInputServerStream),
            (["UDP", "127.0.0.1", 1234], UDPInputServerStream),
            (["FOO"], ZMQStream),
            (["FOO", "BAR"], ZMQStream),
        ],
    )
    def test_valid_input_stream_factory(self, args, expected):
        full_args = [
            "foo",
            args,
            [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
            {"zmq_context": broker.context},
        ]
        stream = input_stream_factory(*full_args)
        assert isinstance(stream, expected)

    @pytest.mark.parametrize(
        "args,expected",
        [
            (["TCP", "127.0.0.1", "1234"], ValueError),
            (["TCP", "127.0.0.1", 1], ValueError),
            (["TCP", "server", "1234"], ValueError),
            (["TCP", "server", 1], ValueError),
            (["TCP", 1, 1024], ValueError),
            (["UDP", "server", "1234"], ValueError),
            (["UDP", "server", 1], ValueError),
            (["FOO", "server", 1024], ValueError),
            (["server", 1234], ValueError),
            ([1], ValueError),
            (1, ValueError),
            ([], ValueError),
            (None, ValueError),
            (["foo", "bar", "foo", 1], ValueError),
        ],
    )
    def test_invalid_input_stream_factory(self, args, expected):
        full_args = [
            "foo",
            args,
            [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
            {"zmq_context": broker.context},
        ]
        with pytest.raises(expected):
            _ = input_stream_factory(*full_args)

    @pytest.mark.parametrize(
        "args,expected",
        [
            (["TCP", "127.0.0.1", 1234], PortOutputStream),
            (["TCP", "localhost", 1234], PortOutputStream),
            (["TCP", "foo", 1234], PortOutputStream),
            (["UDP", "127.0.0.1", 1234], PortOutputStream),
            (["UDP", "localhost", 1234], PortOutputStream),
            (["UDP", "foo", 1234], PortOutputStream),
            ([1234], PortOutputStream),
            (1234, PortOutputStream),
            ([], ZMQStream),
            (None, ZMQStream),
        ],
    )
    def test_valid_output_stream_factory(self, args, expected):
        full_args = [
            "foo",
            "bar",
            args,
            [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
            {"zmq_context": broker.context},
        ]
        stream = output_stream_factory(*full_args)
        assert isinstance(stream, expected)

    @pytest.mark.parametrize(
        "args,expected",
        [
            (["FOO", "127.0.0.1", 1234], ValueError),
            (["UDP", "127.0.0.1", "1234"], ValueError),
            (["UDP", 1, "1234"], ValueError),
        ],
    )
    def test_invalid_output_stream_factory(self, args, expected):
        full_args = [
            "foo",
            "bar",
            args,
            [PacketHandler(input_type=int, output_type=str, packet="CCSDS_HEADER")],
            {"zmq_context": broker.context},
        ]
        with pytest.raises(expected):
            _ = output_stream_factory(*full_args)