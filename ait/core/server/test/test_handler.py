import unittest
import pickle
from nose.tools import *
from unittest import mock

from ait.core import tlm
from ait.core.server.handlers import PacketHandler
from ait.core.server.handlers import CCSDSPacketHandler


class TestCCSDSPacketCheck(unittest.TestCase):
    
    # Check if packet length is at least 7 bytes
    def test_ccsds_packet_length(self):
        handler = CCSDSPacketHandler(packet_types={'01011100111' : 'CCSDS_HEADER'})
        data = bytearray(b'\x02\xE7\x40\x00\x00\x00')
        with self.assertLogs('ait', level='INFO') as cm:
            result = handler.handle(data)
        self.assertIn('less than minimum of 7 bytes', cm.output[0])

    # Check if APID match between config and packet
    def test_ccsds_packet_apid(self):
        handler = CCSDSPacketHandler(packet_types={'00000000000' : 'CCSDS_HEADER'})
        data = bytearray(b'\x02\xE7\x40\x00\x00\x00\x01')
        with self.assertLogs('ait', level='INFO') as cm:
            result = handler.handle(data)
        self.assertIn('not present in config', cm.output[0])

    # Check packet length vs header reported length
    def test_ccsds_packet_header(self):
        handler = CCSDSPacketHandler(packet_types={'01011100111' : 'CCSDS_HEADER'})
        data = bytearray(b'\x02\xE7\x40\x00\x00\x0F\x01')
        with self.assertLogs('ait', level='INFO') as cm:
            result = handler.handle(data)
        self.assertIn('Packet data length is less than stated length in packet primary header', cm.output[0])

    # Check if dumped uid match expected tlm dictionary uid
    def test_ccsds_packet_uid(self):
        handler = CCSDSPacketHandler(packet_types={'01011100111' : 'CCSDS_HEADER'})
        data = bytearray(b'\x02\xE7\x40\x00\x00\x00\x01')

        tlm_dict = tlm.getDefaultDict()
        packet_uid = tlm_dict['CCSDS_HEADER'].uid
        result = handler.handle(data)
        self.assertEqual(packet_uid, pickle.loads(result)[0])


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


class TestCCSDSHandlerClassWithInputOutputTypes(object):
    handler = CCSDSPacketHandler(packet_types={'01011100111' : 'CCSDS_HEADER'}, input_type='int', output_type='str')
    def test_handler_creation(self):
        assert self.handler.input_type is 'int'
        assert self.handler.output_type is 'str'

    @mock.patch('ait.core.server.handlers.CCSDSPacketHandler.handle', return_value='SpecialReturn')
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        data = bytearray(b'\x02\xE7\x40\x00\x00\x00\x01')
        returned = self.handler.handle(data)
        assert returned == 'SpecialReturn'


class TestCCSDSHandlerClassWithoutInputOutputTypes(object):
    handler = CCSDSPacketHandler(packet_types={'01011100111' : 'CCSDS_HEADER'})
    def test_ccsds_handler_default_params(self):
        assert self.handler.input_type is None
        assert self.handler.output_type is None

    @mock.patch('ait.core.server.handlers.CCSDSPacketHandler.handle', return_value='SpecialReturn')
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        data = bytearray(b'\x02\xE7\x40\x00\x00\x00\x01')
        returned = self.handler.handle(data)
        assert returned == 'SpecialReturn'

    def test_handler_repr(self):
        assert self.handler.__repr__() == '<handler.CCSDSPacketHandler>'

