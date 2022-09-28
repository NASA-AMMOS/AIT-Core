import pickle
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


class TestHandlerClassWithInputOutputTypes(object):
    handler = PacketHandler(packet="CCSDS_HEADER", input_type="int", output_type="str")

    def test_handler_creation(self):
        assert self.handler.input_type is "int"
        assert self.handler.output_type is "str"

    @mock.patch(
        "ait.core.server.handlers.PacketHandler.handle", return_value="SpecialReturn"
    )
    def test_execute_handler_returns_handle_return_on_input(self, handle_mock):
        returned = self.handler.handle("2")
        assert returned == "SpecialReturn"


class TestHandlerClassWith1553HSPacket(object):
    tlm_dict = tlm.getDefaultDict()
    pkt_data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01")
    pkt_1553 = tlm_dict['1553_HS_Packet']
    handler = PacketHandler(pkt_data, packet="1553_HS_Packet")

    def test_word_array(self):
        packet = tlm.Packet(self.pkt_1553, self.pkt_data)
        assert packet.words.__len__() == 3.5

    def test_execute_handler_returns_handle_return_on_input(self):
        packet = tlm.Packet(self.pkt_1553, self.pkt_data)
        result = self.handler.handle(packet)
        assert 'Ethernet 1553 packet' in str(result)

    # Test packet length by sending a Ethernet_HS_Packet to a 1553_HS_Packet Handler
    def test_bad_packet_length(self):
        ethernet_pkt = self.tlm_dict['Ethernet_HS_Packet']
        e_packet = tlm.Packet(ethernet_pkt, self.pkt_data)
        with pytest.raises(ValueError):
            self.handler.handle(e_packet)

    def test_packet_name_error_and_no_packet_type(self):
        pkt_data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01")
        with pytest.raises(ValueError):
            PacketHandler(pkt_data, packet="1553_HS_Packe")
        with pytest.raises(ValueError):
            PacketHandler(pkt_data)


class TestHandlerClassWithEthernetHSPacket(object):
    tlm_dict = tlm.getDefaultDict()
    pkt_data = bytearray(b"\x02\xE7\x40\x00\x00\x00\x01\x07\x08\x0a")
    ethernet_pkt = tlm_dict['Ethernet_HS_Packet']
    handler = PacketHandler(pkt_data, packet="Ethernet_HS_Packet")

    def test_word_array(self):
        e_packet = tlm.Packet(self.ethernet_pkt, self.pkt_data)
        assert e_packet.words.__len__() == 5

    def test_execute_handler_returns_handle_return_on_input(self):
        e_packet = tlm.Packet(self.ethernet_pkt, self.pkt_data)
        result = self.handler.handle(e_packet)
        assert 'Ethernet Health and Status Packet' in str(result)

    # Send a 1553 packet to an Ethernet_HS_Packet Handler
    def test_bad_packet_length(self):
        pkt_1553 = self.tlm_dict['1553_HS_Packet']
        packet = tlm.Packet(pkt_1553, self.pkt_data)
        with pytest.raises(ValueError):
            self.handler.handle(packet)


class TestHandlerClassWithoutInputOutputTypes(object):
    handler = PacketHandler(packet="CCSDS_HEADER")

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
