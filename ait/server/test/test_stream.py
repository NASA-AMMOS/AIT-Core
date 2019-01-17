from ait.server.stream import Stream
from ait.server.handlers.ccsds_packet_handler import CcsdsPacketHandler
from nose.tools import *
import mock
import zmq
import ait


class TestStream(object):
    stream = Stream('some_stream',
                    'input_stream',
                    [CcsdsPacketHandler(int, output_type=str)])

    def setUp(self):
        self.stream.handlers = [CcsdsPacketHandler(int, output_type=str)]

    def test_stream_creation(self):
        assert self.stream.name is 'some_stream'
        assert self.stream.input_ is 'input_stream'
        assert len(self.stream.handlers) == 1
        assert type(self.stream.handlers[0]) == CcsdsPacketHandler
        assert self.stream.context == ait.broker.context
        assert type(self.stream.pub) == zmq.sugar.socket.Socket
        assert type(self.stream.sub) == zmq.sugar.socket.Socket

    def test_repr(self):
        assert self.stream.__repr__() == '<Stream name=some_stream>'

    @mock.patch.object(ait.server.handlers.ccsds_packet_handler.CcsdsPacketHandler, 'execute_handler')
    def test_process(self, execute_handler_mock):
        self.stream.process('input_data')
        execute_handler_mock.assert_called_with('input_data')

    def test_valid_workflow_one_handler(self):
        assert self.stream.valid_workflow() is True

    def test_valid_workflow_more_handlers(self):
        self.stream.handlers.append(CcsdsPacketHandler(str))
        assert self.stream.valid_workflow() is True

    def test_invalid_workflow_more_handlers(self):
        self.stream.handlers.append(CcsdsPacketHandler(int))
        assert self.stream.valid_workflow() is False

    def test_type(self):
        # not registered with broker
        assert self.stream.type == 'Stream'

        # in broker inbound_streams
        ait.broker.inbound_streams = [self.stream]
        assert self.stream.type == 'Inbound Stream'

        # in broker outbound_streams
        ait.broker.inbound_streams = [ ]
        ait.broker.outbound_streams = [self.stream]
        assert self.stream.type == 'Outbound Stream'

    def test_stream_creation_invalid_workflow(self):
        with assert_raises_regexp(ValueError,
                                  'Sequential workflow inputs and outputs ' +
                                  'are not compatible. Workflow is invalid.'):
            Stream('some_stream',
                   'input_stream',
                   [CcsdsPacketHandler(int, output_type=str),
                    CcsdsPacketHandler(int)])
