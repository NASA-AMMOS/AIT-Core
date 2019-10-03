from nose.tools import *
from unittest import mock

from ait.core.server.handlers import PacketHandler


class TestHandlerClassWithInputOutputTypes(object):
    handler = PacketHandler(packet='CCSDS_HEADER', input_type='int', output_type='str')

    def test_handler_creation(self):
        assert self.handler.input_type is 'int'
        assert self.handler.output_type is 'str'

    @mock.patch('ait.core.server.handlers.PacketHandler.handle', return_value='SpecialReturn')
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        returned = self.handler.handle('2')
        assert returned == 'SpecialReturn'


class TestHandlerClassWithoutInputOutputTypes(object):
    handler = PacketHandler(packet='CCSDS_HEADER')

    def test_handler_default_params(self):
        assert self.handler.input_type is None
        assert self.handler.output_type is None

    @mock.patch('ait.core.server.handlers.PacketHandler.handle', return_value='SpecialReturn')
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        returned = self.handler.handle('2')
        assert returned == 'SpecialReturn'

    def test_handler_repr(self):
        assert self.handler.__repr__() == '<handler.PacketHandler>'
