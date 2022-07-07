"""
Implements a plugin which routes CCSDS packets by APID
"""
import os
import yaml
from ait.core.server.plugins import Plugin
from ait.core import tlm, log


class APIDRouter(Plugin):
    """
    Routes CCSDS packets by APID according to a routing table defined by a yaml file.
    Arguments to the range operator are inclusive.
    (i.e. range[40,50] adds APIDs 40-50 inclusive to the topic, not 40-49)
    The exclude operator must come after the range operator.

    example in config.yaml:

    - plugin:
        name: ait.core.server.plugins.apid_routing.APIDRouter
        inputs:
            - AOS_to_CCSDS
        default_topic: default_ccsds_tlm_topic
        routing_table:
            path: packet_routing_table.yaml

    example routing table .yaml file:

    output_topics:
        - telem_topic_1:
            - 1
            - 2
        - telem_stream_1:
            - 3
            - 4
            - range:
                - 40
                - 50
            - exclude:
                - 43
        - telem_topic_2:
            - 5
            - range:
                - 12
                - 19
            - exclude:
                - 14
                - 18
        - GUI_input_stream:
            - range:
                - 1
                - 100
            - exclude:
                - 87
        - DataArchive:
            - range:
                - 1
                - 138
    """
    def __init__(self, inputs=None, outputs=None, zmq_args=None, routing_table=None, default_topic=None):

        super().__init__(inputs, outputs, zmq_args)

        self.default_topic = default_topic

        if 'path' in routing_table:
            self.routing_table_object = self.load_table_yaml(routing_table['path'], tlm.getDefaultDict())
        else:
            self.routing_table_object = None
            log.error("no path specified for routing table")
        if self.routing_table_object is None:
            log.error("Unable to load routing table .yaml file")

    def process(self, input_data):
        """
        publishes incoming CCSDS packets to the routes specified in the routing table

        :param input_data: CCSDS packet as bytes
        :type input_data: bytes, bytearray
        """
        packet_apid = self.get_packet_apid(input_data)
        topics = self.routing_table_object[packet_apid]
        for route in topics:
            self.publish(input_data, route)

    def get_packet_apid(self, packet):
        """
        Returns the APID (as integer) for a given packet (bytearray)
        Assumes that the APID is the last 11 bits of the first two bytes

        :param packet: CCSDS packet as bytes
        :type packet: bytes, bytearray
        :returns: packet APID
        :rtype: int
        """
        packet_apid_bits = bytearray(b1 & b2 for b1, b2 in zip(packet[0:2], bytearray(b'\x07\xff')))
        apid = int.from_bytes(packet_apid_bits, byteorder='big')
        return apid

    def add_topic_to_table(self, routing_table, apid, topic_name):
        """
        Returns an updated table with the topic_name added to the entry for the specified APID

        :param routing_table: routing table to be updated
        :param apid: entry in routing table
        :param topic_name: topic name to add to entry in routing table
        :type routing_table: dict
        :type apid: int
        :type topic_name: string
        :returns: updated routing table
        :rtype: dict
        """
        temp_entry = routing_table[apid]
        temp_entry.append(topic_name)
        routing_table[apid] = temp_entry
        return routing_table

    def add_range_to_table(self, routing_table, range_array, topic_name):
        """
        Adds a range of APIDs to the routing table.
        The range_array argument is an array of form [beginning, end].
        This function is inclusive of all values.
        I.e. if range_array is [5, 9], APIDs 5-9 inclusive will be added (not 5-8).

        :param routing_table: routing table to be updated
        :param range_array: list containing beginning and end values for entries to update
        :param topic_name: topic name to add to entries in routing table
        :type routing_table: dict
        :type range_array: list
        :type topic_name: string
        :returns: updated routing table
        :rtype: dict
        """
        beginning = range_array[0]
        end = range_array[1]
        for apid in range(beginning, end + 1):
            routing_table = self.add_topic_to_table(routing_table, apid, topic_name)
        return routing_table

    def remove_from_table(self, routing_table, apid_array, topic_name):
        """
        Removes a topic name from all the APIDs in the apid_array argument.

        :param routing_table: routing table to be updated
        :param apid_array: list containing entries to update
        :param topic_name: topic name to remove from entries in routing table
        :type routing_table: dict
        :type apid_array: list
        :type topic_name: string
        :returns: updated routing table
        :rtype: dict
        """
        for apid in apid_array:
            temp_entry = routing_table[apid]
            if topic_name in temp_entry:
                temp_entry.remove(topic_name)
            routing_table[apid] = temp_entry
        return routing_table

    def load_table_yaml(self, routing_table_path, tlm_dict):
        """
        Reads a .yaml file and returns a dictionary of format {apid1: [streams], apid2: [streams]}

        :param routing_table_path: path to yaml file containing routing table
        :param tlm_dict: AIT telemetry dictionary
        :type routing_table_path: string
        :returns: routing table
        :rtype: dict
        """
        routing_table = {}
        error = None

        for packet_name in tlm_dict:
            packet_apid = tlm_dict[packet_name].apid  # assuming apid is defined in dictionary
            routing_table[packet_apid] = [self.default_topic]

        if routing_table_path is None:
            error = "No path specified for routing_table_path parameter"
            log.error(error)
            return None

        if os.path.isfile(routing_table_path):
            with open(routing_table_path, "rb") as stream:
                yaml_file_as_dict = yaml.load(stream, Loader=yaml.Loader)
        else:
            error = f"File path {routing_table_path} does not exist"
            log.error(error)
            return None

        for telem_stream_entry in yaml_file_as_dict["output_topics"]:
            # telem_stream_entry is a dict with one entry
            for telem_stream_name in telem_stream_entry:
                for value in telem_stream_entry[telem_stream_name]:
                    if isinstance(value, int):  # assume integer value is apid
                        apid = value
                        routing_table = self.add_topic_to_table(routing_table, apid, telem_stream_name)
                    elif isinstance(value, dict):
                        for operator in value:
                            if operator == "range":
                                routing_table = self.add_range_to_table(routing_table, value["range"], telem_stream_name)
                            if operator == "exclude":
                                routing_table = self.remove_from_table(routing_table, value["exclude"], telem_stream_name)
                    else:
                        log.error("Error while parsing table.yaml: encountered a value which is neither an integer nor a dictionary")

        return routing_table
