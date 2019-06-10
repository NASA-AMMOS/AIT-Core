from abc import ABCMeta, abstractmethod
import cPickle as pickle
import binascii
import ait.core.log

from ait.core import tlm

class Handler(object):
    """
    This is the base Handler class that all custom handlers must inherit
    from. All custom handlers must implement the handle method, which will
    called by the stream the handler is attached to when the stream receives
    data.
    """
    __metaclass__ = ABCMeta

    def __init__(self, input_type=None, output_type=None, **kwargs):
        """
        Params:
            input_type:   (optional) Specifies expected input type, used to
                                     validate handler workflow. Defaults to None.
            output_type:  (optional) Specifies expected output type, used to
                                     validate handler workflow. Defaults to None
            **kwargs:     (optional) Requirements dependent on child class.
        """
        self.input_type = input_type
        self.output_type = output_type

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return '<handler.%s>' % (self.__class__.__name__)

    @abstractmethod
    def handle(self, input_data):
        """
        Not implemented by base Handler class.
        This handle method must be implemented by any custom handler class
        that inherits from this base Handler.

        Params:
            input_data: If this is a stream's first handler, the input_data will
                        be the message received by the stream. Otherwise it will
                        be the output of the previous handler.
        """
        pass


class PacketHandler(Handler):

    def __init__(self, input_type=None, output_type=None, **kwargs):
        """
        Params:
            input_type:   (optional) Specifies expected input type, used to
                                     validate handler workflow. Defaults to None.
            output_type:  (optional) Specifies expected output type, used to
                                     validate handler workflow. Defaults to None
            **kwargs:
                packet:   (required) Name of packet, present in default tlm dict.
        Raises:
            ValueError:    If packet is not present in kwargs.
                           If packet is specified but not present in default tlm dict.
        """
        super(PacketHandler, self).__init__(input_type, output_type)
        self.packet = kwargs.get('packet', None)

        if not self.packet:
            msg = 'PacketHandler: No packet name provided in handler config as key "packet"'
            raise ValueError(msg)

        tlm_dict = tlm.getDefaultDict()
        if self.packet not in tlm_dict:
            msg = 'PacketHandler: Packet name {} not present in telemetry dictionary'.format(self.packet)
            msg += ' Available packet types are {}'.format(tlm_dict.keys())
            raise ValueError(msg)

        self._pkt_defn = tlm_dict[self.packet]

    def handle(self, input_data):
        """
        Params:
            input_data:   message received by stream
        Returns:
            tuple of packet UID and message received by stream
        """
        return pickle.dumps((self._pkt_defn.uid, input_data), 2)


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
        self.packet_types = kwargs['packet_types']
        self.packet_secondary_header_length = kwargs.get('packet_secondary_header_length', 0)

        # Check if all packet names in config are in telemetry dictionary
        tlm_dict = tlm.getDefaultDict()
        for packet_name in self.packet_types.values():
            if packet_name not in tlm_dict.keys():
                msg = 'CCSDSPacketHandler: Packet name {} not present in telemetry dictionary.'.format(packet_name)
                msg += ' Available packet types are {}'.format(tlm_dict.keys())
                raise ValueError(msg)

    def handle(self, input_data):
        """
        Params:
            packet:    CCSDS packet
        Returns:
            tuple of packet UID and packet data field
        """

        # Convert input_data (packed binary data string) into bytearray
        packet = bytearray(input_data)

        # Check if packet length is at least 7 bytes
        primary_header_length = 6
        if (len(packet) < primary_header_length + 1):
            ait.core.log.info('CCSDSPacketHandler: Received packet length is less than minimum of 7 bytes.')
            return

        # Extract APID from packet
        packet_apid = str(bin(int(binascii.hexlify(packet[0:2]), 16) & 0x07FF))[2:].zfill(11)

        # Check if packet_apid matches with an APID in the config
        config_apid = ''
        for i in self.packet_types:
            if self.comp_apid(packet_apid, i):
                config_apid = i
                break
        if not config_apid:
            msg = 'CCSDSPacketHandler: Packet APID {} not present in config.'.format(packet_apid)
            msg += ' Available packet APIDs are {}'.format(self.packet_types.keys())
            ait.core.log.info(msg)
            return

        # Map APID to packet name in config to get UID from telemetry dictionary
        packet_name = self.packet_types[config_apid]
        tlm_dict = tlm.getDefaultDict()
        packet_uid = tlm_dict[packet_name].uid

        # Extract user data field from packet
        packet_data_length = int(binascii.hexlify(packet[4:6]), 16) + 1
        if (len(packet) < primary_header_length + packet_data_length):
            ait.core.log.info(
                'CCSDSPacketHandler: Packet data length is less than stated length in packet primary header.')
            return
        udf_length = packet_data_length - self.packet_secondary_header_length
        udf_start = primary_header_length + self.packet_secondary_header_length
        user_data_field = packet[udf_start:udf_start + udf_length + 1]

        ait.core.log.info(packet_apid)
        ait.core.log.info(user_data_field[0])
        ait.core.log.info(user_data_field[1])
        ait.core.log.info(user_data_field[2])

        return pickle.dumps((packet_uid, user_data_field), 2)

    def comp_apid(self, server_apid, config_apid):
        """
        Params:
            server_apid:  APID from server
            config_apid:  APID from config, X represents bit not used
        Returns:
            True if server_apid matches config_apid
            False otherwise
        """
        for i in range(11):
            if config_apid[i] != 'X' and config_apid[i] != server_apid[i]:
                return False
        return True
