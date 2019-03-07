from nose.tools import *
import mock

from ait.core.server.handler import PacketHandler


class TestHandlerClassWithInputOutputTypes(object):
    handler = PacketHandler(packet='CCSDS_HEADER', input_type='int', output_type='str')

    def test_handler_creation(self):
        assert self.handler.input_type is 'int'
        assert self.handler.output_type is 'str'

    def test_validate_input_types(self):
        # test successful conversions
        valid = self.handler.validate_input(2)
        assert valid == 2
        valid = self.handler.validate_input('2')
        assert valid == 2
        # test unsuccessful conversions
        with assert_raises_regexp(ValueError, 'invalid literal'):
            self.handler.validate_input('a string')

    @mock.patch('ait.core.server.handler.PacketHandler.handle', return_value='SpecialReturn')
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        returned = self.handler.execute_handler('2')
        assert returned == 'SpecialReturn'

    def test_execute_handler_raises_error_on_invalid_input(self):
        with assert_raises_regexp(ValueError, 'Input is not of valid type: '):
            self.handler.execute_handler('invalid input data')


class TestHandlerClassWithoutInputOutputTypes(object):
    handler = PacketHandler(packet='CCSDS_HEADER')

    def test_handler_default_params(self):
        assert self.handler.input_type is None
        assert self.handler.output_type is None

    def test_validate_input_no_types(self):
        valid = self.handler.validate_input('anything')
        assert valid == 'anything'

    @mock.patch('ait.core.server.handler.PacketHandler.handle', return_value='SpecialReturn')
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        returned = self.handler.execute_handler('2')
        assert returned == 'SpecialReturn'

    def test_handler_repr(self):
        assert self.handler.__repr__() == '<handler.PacketHandler>'
