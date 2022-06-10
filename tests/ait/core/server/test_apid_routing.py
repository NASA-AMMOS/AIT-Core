import unittest

from unittest.mock import patch
from ait.core import log
from ait.core.server.plugins.apid_routing import APIDRouter
from ait.core.util import TestFile


class TestPacket:
    def __init__(self, apid=0):
        self.apid = apid


def create_test_dict(number_of_packets = 150):
    test_dict = {}
    for i in range(1, number_of_packets+1):
        packet_name = f"Packet_{i}"
        test_dict[packet_name] = TestPacket(apid = i)
    return test_dict


class TestPacketRouting(unittest.TestCase):
    def routing_table_yaml():
        """
        # Call this function to return the yaml string below

        output_topics:
            - telem_topic_1:
                - 1
                - 7
            - telem_topic_2:
                - 2
                - range:
                    - 4
                    - 9
                - exclude:
                    - 6
        """

        pass

    with TestFile(routing_table_yaml.__doc__, "wt") as filename:
        def new_init(self, routing_table=None, default_topic=None):
            self.default_topic = default_topic

            if 'path' in routing_table:
                self.routing_table_object = self.load_table_yaml(routing_table['path'], create_test_dict(10))
            else:
                self.routing_table_object = None
                log.error("no path specified for routing table")
            if self.routing_table_object is None:
                log.error("Unable to load routing table .yaml file")

        with patch.object(APIDRouter, '__init__', new_init):
            router_plugin_instance = APIDRouter(routing_table={'path': filename}, default_topic= "test_default_topic")

    def test_routing_table(self):
        test_routing_table_dict = {
            1: ['test_default_topic', 'telem_topic_1'], 
            2: ['test_default_topic', 'telem_topic_2'], 
            3: ['test_default_topic'], 
            4: ['test_default_topic', 'telem_topic_2'], 
            5: ['test_default_topic', 'telem_topic_2'], 
            6: ['test_default_topic'], 
            7: ['test_default_topic', 'telem_topic_1', 'telem_topic_2'], 
            8: ['test_default_topic', 'telem_topic_2'], 
            9: ['test_default_topic', 'telem_topic_2'], 
            10: ['test_default_topic']
            }
        self.assertEqual(self.router_plugin_instance.routing_table_object, test_routing_table_dict)

    def test_apid_extraction1(self):
        test_bytearray = bytearray(b'\x00\x1f\x75\x94\xfa\xdc\x43\x90\x9a\x8c\xff\xe0')
        self.assertEqual(self.router_plugin_instance.get_packet_apid(test_bytearray), 31)

    def test_apid_extraction2(self):
        test_bytearray = bytearray(b'\x01\x03\x75\x94\xfa\xdc\x43\x90\x9a\x8c\xff\xe0')
        self.assertEqual(self.router_plugin_instance.get_packet_apid(test_bytearray), 259)

    def test_get_topics(self):
        test_bytearray = bytearray(b'\x00\x07\x75\x94\xfa\xdc\x43\x90\x9a\x8c\xff\xe0')
        test_bytearray_apid = self.router_plugin_instance.get_packet_apid(test_bytearray)
        expected_topics = ['test_default_topic', 'telem_topic_1', 'telem_topic_2']
        self.assertEqual(self.router_plugin_instance.routing_table_object[test_bytearray_apid], expected_topics)
