import pickle
import _pickle
import pytest
import unittest
from unittest import mock

from ait.core import tlm
from ait.core.server.handlers import CCSDSPacketHandler
from ait.core.server.handlers import PacketHandler


class TestCCSDSPacketCheck(unittest.TestCase):
    # Check if packet length is at least 7 bytes
    def test_ccsds_packet_length(self):
        handler = CCSDSPacketHandler(packet_types={"01011100111": "CCSDS_HEADER"})
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00")
        with self.assertLogs("ait", level="INFO") as cm:
            handler.handle(data)
        self.assertIn("less than minimum of 7 bytes", cm.output[0])

    # Check if APID match between config and packet
    def test_ccsds_packet_apid(self):
        handler = CCSDSPacketHandler(packet_types={"00000000000": "CCSDS_HEADER"})
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01")
        with self.assertLogs("ait", level="INFO") as cm:
            handler.handle(data)
        self.assertIn("not present in config", cm.output[0])

    # Check packet length vs header reported length
    def test_ccsds_packet_header(self):
        handler = CCSDSPacketHandler(packet_types={"01011100111": "CCSDS_HEADER"})
        data = bytearray(b"\x02\xE7\x40\x00\x00\x0F\x01")
        with self.assertLogs("ait", level="INFO") as cm:
            handler.handle(data)
        self.assertIn(
            "Packet data length is less than stated length in packet primary header",
            cm.output[0],
        )

    def test_packet_name_not_present(self):
        with pytest.raises(ValueError):
            CCSDSPacketHandler(packet_types={"01011100111": "CCSDS_"})

    # Check if dumped uid match expected tlm dictionary uid
    def test_ccsds_packet_uid(self):
        handler = CCSDSPacketHandler(packet_types={"01011100111": "CCSDS_HEADER"})
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01")

        tlm_dict = tlm.getDefaultDict()
        packet_uid = tlm_dict["CCSDS_HEADER"].uid
        result = handler.handle(data)
        self.assertEqual(packet_uid, pickle.loads(result)[0])


class TestCCSDSHandlerClassWithInputOutputTypes(object):
    handler = CCSDSPacketHandler(
        packet_types={"01011100111": "CCSDS_HEADER"},
        input_type="int",
        output_type="str",
    )

    def test_handler_creation(self):
        assert self.handler.input_type is "int"
        assert self.handler.output_type is "str"

    @mock.patch(
        "ait.core.server.handlers.CCSDSPacketHandler.handle",
        return_value="SpecialReturn",
    )
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01")
        returned = self.handler.handle(data)
        assert returned == "SpecialReturn"


class TestCCSDSHandlerClassWithoutInputOutputTypes(object):
    handler = CCSDSPacketHandler(packet_types={"01011100111": "CCSDS_HEADER"})

    def test_ccsds_handler_default_params(self):
        assert self.handler.input_type is None
        assert self.handler.output_type is None

    @mock.patch(
        "ait.core.server.handlers.CCSDSPacketHandler.handle",
        return_value="SpecialReturn",
    )
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01")
        returned = self.handler.handle(data)
        assert returned == "SpecialReturn"

    def test_handler_repr(self):
        assert self.handler.__repr__() == "<handler.CCSDSPacketHandler>"


class TestHandlerClassWith1553HSPacket(unittest.TestCase):
    tlm_dict = tlm.getDefaultDict()
    pkt_data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01\x02\x03\x04")
    pkt_1553 = tlm_dict['1553_HS_Packet']
    handler = PacketHandler(packet="1553_HS_Packet")

    def test_word_array(self):
        packet = tlm.Packet(self.pkt_1553, self.pkt_data)
        assert packet.words.__len__() == self.pkt_1553.nbytes/2

    def test_1553_uid(self):
        packet_uid = self.tlm_dict["1553_HS_Packet"].uid
        result = self.handler.handle(self.pkt_data)
        self.assertEqual(packet_uid, pickle.loads(result)[0])

    # Send only 5 bytes 1553 Packet expects 10 bytes
    def test_bad_packet_length(self):
        pkt_data = bytearray(b"\x02\xE7\x40\x00\x00")
        with self.assertLogs("ait", level="INFO") as cm:
            self.handler.handle(pkt_data)
        self.assertIn(
            "Packet data length does not match packet definition.",
            cm.output[0],
        )

    def test_packet_name_error_and_no_packet_type(self):
        with pytest.raises(ValueError):
            PacketHandler(packet="")


class TestHandlerClassWithEthernetHSPacket(unittest.TestCase):
    tlm_dict = tlm.getDefaultDict()
    pkt_data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01\x40\x00\x03\x02\xE7\x40\x00\x00\x00\x01\x40\x00\x03"
                         b"\x02\xE7\x40\x00\x00\x00\x01\x40\x00\x03\x02\xE7\x40\x00\x00\x00\x01")
    ethernet_pkt_def = tlm_dict['Ethernet_HS_Packet']
    handler = PacketHandler(packet="Ethernet_HS_Packet")

    def test_word_array(self):
        e_packet = tlm.Packet(self.ethernet_pkt_def, self.pkt_data)
        assert e_packet.words.__len__() == self.ethernet_pkt_def.nbytes/2.0

    def test_1553_uid(self):
        packet_uid = self.tlm_dict["Ethernet_HS_Packet"].uid
        result = self.handler.handle(self.pkt_data)
        self.assertEqual(packet_uid, pickle.loads(result)[0])

    # Ethernet packet expects 37 bytes 1552 expects 10
    def test_bad_packet_length(self):
        pkt_data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01\x07\x08\x0a")
        with self.assertLogs("ait", level="INFO") as cm:
            self.handler.handle(pkt_data)
        self.assertIn(
            "Packet data length does not match packet definition.",
            cm.output[0],
        )


class TestHandlerClassWithoutInputOutputTypes(object):
    handler = PacketHandler(packet="Ethernet_HS_Packet")

    def test_handler_default_params(self):
        assert self.handler.input_type is None
        assert self.handler.output_type is None

    @mock.patch(
        "ait.core.server.handlers.PacketHandler.handle", return_value="SpecialReturn"
    )
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        returned = self.handler.handle("2")
        assert returned == "SpecialReturn"

    def test_handler_repr(self):
        assert self.handler.__repr__() == "<handler.PacketHandler>"


class TestHandlerClassWithInputOutputTypes(object):
    handler = PacketHandler(
        packet='1553_HS_Packet',
        input_type="int",
        output_type="str",
    )

    def test_handler_creation(self):
        assert self.handler.input_type is "int"
        assert self.handler.output_type is "str"

    @mock.patch(
        "ait.core.server.handlers.PacketHandler.handle",
        return_value="SpecialReturn",
    )
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01\x02\x03\x04")
        returned = self.handler.handle(data)
        assert returned == "SpecialReturn"


class TestHandlerClassWithoutInputOutputTypes(object):
    handler = PacketHandler(packet="Ethernet_HS_Packet")

    def test_ccsds_handler_default_params(self):
        assert self.handler.input_type is None
        assert self.handler.output_type is None

    @mock.patch(
        "ait.core.server.handlers.PacketHandler.handle",
        return_value="SpecialReturn",
    )
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        # Note: Using 'mock' handler, the data will not be tested for length.
        data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01\x02\x03\x04")
        returned = self.handler.handle(data)
        assert returned == "SpecialReturn"

    def test_handler_repr(self):
        assert self.handler.__repr__() == "<handler.PacketHandler>"
