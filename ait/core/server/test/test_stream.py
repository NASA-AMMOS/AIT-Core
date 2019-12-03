from nose.tools import *
from unittest import mock
import zmq.green

import ait.core
from ait.core.server.broker import Broker
from ait.core.server.stream import ZMQStream
from ait.core.server.handlers import PacketHandler


class TestStream(object):
    broker = Broker()
    stream = ZMQStream('some_stream',
                       ['input_stream'],
                       [PacketHandler(input_type=int,
                                      output_type=str,
                                      packet='CCSDS_HEADER')],
                       zmq_args={'zmq_context': broker.context})

    def setUp(self):
        self.stream.handlers = [PacketHandler(input_type=int,
                                              output_type=str,
                                              packet='CCSDS_HEADER')]

    def test_stream_creation(self):
        assert self.stream.name is 'some_stream'
        assert self.stream.inputs == ['input_stream']
        assert len(self.stream.handlers) == 1
        assert type(self.stream.handlers[0]) == PacketHandler
        assert self.stream.context == self.broker.context
        assert type(self.stream.pub) == zmq.green.core._Socket
        assert type(self.stream.sub) == zmq.green.core._Socket

    def test_repr(self):
        assert self.stream.__repr__() == '<ZMQStream name=some_stream>'

    @mock.patch.object(PacketHandler, 'handle')
    def test_process(self, execute_handler_mock):
        self.stream.process('input_data')
        execute_handler_mock.assert_called_with('input_data')

    def test_valid_workflow_one_handler(self):
        assert self.stream.valid_workflow() is True

    def test_valid_workflow_more_handlers(self):
        self.stream.handlers.append(PacketHandler(input_type=str, packet='CCSDS_HEADER'))
        assert self.stream.valid_workflow() is True

    def test_invalid_workflow_more_handlers(self):
        self.stream.handlers.append(PacketHandler(input_type=int, packet='CCSDS_HEADER'))
        assert self.stream.valid_workflow() is False

    def test_stream_creation_invalid_workflow(self):
        with assert_raises_regexp(ValueError,
                                  'Sequential workflow inputs and outputs ' +
                                  'are not compatible. Workflow is invalid.'):
            ZMQStream('some_stream',
                           'input_stream',
                           [PacketHandler(input_type=int, output_type=str, packet='CCSDS_HEADER'),
                            PacketHandler(input_type=int, packet='CCSDS_HEADER')],
                            zmq_args={'zmq_context': self.broker.context})
