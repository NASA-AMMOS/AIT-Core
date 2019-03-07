from nose.tools import *
import mock
import zmq.green

import ait.core
from ait.core.server.broker import Broker
from ait.core.server.stream import ZMQInputStream
from ait.core.server.handler import Handler


class TestStream(object):
    broker = Broker()
    stream = ZMQInputStream('some_stream',
                            'input_stream',
                            [Handler(input_type=int,
                                            output_type=str)],
                            zmq_args={'zmq_context': broker.context})

    def setUp(self):
        self.stream.handlers = [Handler(input_type=int,
                                               output_type=str)]

    def test_stream_creation(self):
        assert self.stream.name is 'some_stream'
        assert self.stream.input_ is 'input_stream'
        assert len(self.stream.handlers) == 1
        assert type(self.stream.handlers[0]) == Handler
        assert self.stream.context == self.broker.context
        print(type(self.stream.pub))
        assert type(self.stream.pub) == zmq.green.core._Socket
        assert type(self.stream.sub) == zmq.green.core._Socket

    def test_repr(self):
        assert self.stream.__repr__() == '<<class \'ait.core.server.stream.ZMQInputStream\'> name=some_stream>'

    @mock.patch.object(Handler, 'execute_handler')
    def test_process(self, execute_handler_mock):
        self.stream.process('input_data')
        execute_handler_mock.assert_called_with('input_data')

    def test_valid_workflow_one_handler(self):
        assert self.stream.valid_workflow() is True

    def test_valid_workflow_more_handlers(self):
        self.stream.handlers.append(Handler(input_type=str))
        assert self.stream.valid_workflow() is True

    def test_invalid_workflow_more_handlers(self):
        self.stream.handlers.append(Handler(input_type=int))
        assert self.stream.valid_workflow() is False

    def test_stream_creation_invalid_workflow(self):
        with assert_raises_regexp(ValueError,
                                  'Sequential workflow inputs and outputs ' +
                                  'are not compatible. Workflow is invalid.'):
            ZMQInputStream('some_stream',
                           'input_stream',
                           [Handler(input_type=int, output_type=str),
                            Handler(input_type=int)],
                            zmq_args={'zmq_context': self.broker.context})
