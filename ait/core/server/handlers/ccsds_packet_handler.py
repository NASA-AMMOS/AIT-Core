import pickle
import binascii
import ait.core.log

from ait.core.server.handler import Handler
from ait.core import tlm


class CCSDSPacketHandler(Handler):
    """
    This CCSDS handler provides a way to accept multiple packet types on a
    single stream and have them be processed. This handler takes a string of
    raw binary data containing CCSDS packet data. It maps the APID of
    the packet to a packet name from the config, and then uses the packet name
    to get the UID from the default telemetry dictionary. The user data field
    is extracted from the raw binary data, and a tuple of the UID and user data
    field is returned.
    """

    def __init__(self, input_type=None, output_type=None, **kwargs):
        """
        Params:
            input_type:   (optional) Specifies expected input type, used to
                                     validate handler workflow. Defaults to None.
            output_type:  (optional) Specifies expected output type, used to
                                     validate handler workflow. Defaults to None
            packet_types: (required) APID value (string) : packet name (string) pairs
                                     APID value can use 'X' to mask out a bit
                                     For example, 'XXXXX1011XXX' means only bits 6-9 represent the APID
            packet_secondary_header_length: (optional) Length of secondary header in octets.
                                                       Defaults to 0.
        Raises:
            ValueError:   If packet in config is not present in default tlm dict.
        """
        super(CCSDSPacketHandler, self).__init__(input_type, output_type)
        self.packet_types = kwargs["packet_types"]
        self.packet_secondary_header_length = kwargs.get(
            "packet_secondary_header_length", 0
        )

        # Check if all packet names in config are in telemetry dictionary
        tlm_dict = tlm.getDefaultDict()
        for packet_name in self.packet_types.values():
            if packet_name not in tlm_dict.keys():
                msg = "CCSDSPacketHandler: Packet name {} not present in telemetry dictionary.".format(
                    packet_name
                )
                msg += " Available packet types are {}".format(tlm_dict.keys())
                raise ValueError(msg)

    def handle(self, input_data):
        """
        Params:
            packet:    CCSDS packet
        Returns:
            tuple of packet UID and packet data field
        """

        # Check if packet length is at least 7 bytes
        primary_header_length = 6
        if len(input_data) < primary_header_length + 1:
            ait.core.log.info(
                "CCSDSPacketHandler: Received packet length is less than minimum of 7 bytes."
            )
            return

        # Extract APID from packet
        packet_apid = str(bin(int(binascii.hexlify(input_data[0:2]), 16) & 0x07FF))[
            2:
        ].zfill(11)

        # Check if packet_apid matches with an APID in the config
        config_apid = self.comp_apid(packet_apid)
        if not config_apid:
            msg = "CCSDSPacketHandler: Packet APID {} not present in config.".format(
                packet_apid
            )
            msg += " Available packet APIDs are {}".format(self.packet_types.keys())
            ait.core.log.info(msg)
            return

        # Map APID to packet name in config to get UID from telemetry dictionary
        packet_name = self.packet_types[config_apid]
        tlm_dict = tlm.getDefaultDict()
        packet_uid = tlm_dict[packet_name].uid

        # Extract user data field from packet
        packet_data_length = int(binascii.hexlify(input_data[4:6]), 16) + 1
        if len(input_data) < primary_header_length + packet_data_length:
            ait.core.log.info(
                "CCSDSPacketHandler: Packet data length is less than stated length in packet primary header."
            )
            return
        udf_length = packet_data_length - self.packet_secondary_header_length
        udf_start = primary_header_length + self.packet_secondary_header_length
        user_data_field = input_data[udf_start : udf_start + udf_length + 1]

        return pickle.dumps((packet_uid, user_data_field), 2)

    def comp_apid(self, server_apid):
        """
        Params:
            server_apid:  APID from server
        Returns:
            Matching config_apid if one is present in config
            None otherwise
        """
        for config_apid in self.packet_types:
            match = True
            for i in range(11):
                if config_apid[i] != "X" and config_apid[i] != server_apid[i]:
                    match = False
                    break
            if match:
                return config_apid
        return None
