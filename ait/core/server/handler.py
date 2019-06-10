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
        """
        super(PacketHandler, self).__init__(input_type, output_type)
        self.packet = kwargs.get('packet', None)

        if not self.packet:
            msg = 'PacketHandler: No packet name provided in handler config as key "packet"'
            raise ValueError(msg)

        tlm_dict = tlm.getDefaultDict()
        if self.packet not in tlm_dict:
            return

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
    packed binary data (packed by struct) containing CCSDS packet data. It then
    maps the APID of the packet to a packet name from the config. Using this
    packet name, it returns the UID and user data field.
    """
    def __init__(self, input_type=None, output_type=None, **kwargs):
        """
        Params:
            input_type:   (optional) Specifies expected input type, used to
                                     validate handler workflow. Defaults to None.
            output_type:  (optional) Specifies expected output type, used to
                                     validate handler workflow. Defaults to None
            packet_types: (required) APID value : packet name pairs
            packet_secondary_header_length: (optional) Length of secondary header in octets.
                                                       Defaults to 0.
        Raises:
            ValueError:   If packet in config is not present in default tlm dict.
        """
        super(CCSDSPacketHandler, self).__init__(input_type, output_type)
        self.packet_types = kwargs['packet_types']
        self.packet_secondary_header_length = kwargs.get('packet_secondary_header_length', 0)
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
        try:
            packet = bytearray(input_data)
            packet_apid = int(binascii.hexlify(packet[6:8]), 16) & 0x07FF
            packet_name = self.packet_types[packet_apid]
            tlm_dict = tlm.getDefaultDict()
            packet_uid = tlm_dict[packet_name].uid

            packet_data_length = int(binascii.hexlify(packet[10:12]), 16) + 1
            udf_length = packet_data_length - self.packet_secondary_header_length
            udf_start = 12 + self.packet_secondary_header_length
            user_data_field = packet[udf_start:udf_start + udf_length]
            return pickle.dumps((packet_uid, user_data_field), 2)
        except:
            return