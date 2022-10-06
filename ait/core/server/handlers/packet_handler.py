import pickle

from ait.core.server.handler import Handler
from ait.core import tlm


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
        self.packet_type = kwargs.get("packet", None)
        self.tlm_dict = tlm.getDefaultDict()

        if not self.packet_type:
            msg = f'PacketHandler: No packet type provided in handler config as key "packet"'
            raise ValueError(msg)

        if self.packet_type not in self.tlm_dict:
            msg = f"PacketHandler: Packet name '{self.packet_type}' not present in telemetry dictionary."
            msg += f" Available packet types are {self.tlm_dict.keys()}"
            raise ValueError(msg)

        self._pkt_defn = self.tlm_dict[self.packet_type]

    def get_packet_lengths(self):
        """
        Makes a dictionary of packet.name : number of bytes in the packet
            e.g.  'Ethernet_HS_Packet': 37

        Return:  dictionary

        """
        pkt_len_dict = {}
        for i in self.tlm_dict.keys():
            pkt_len_dict[i] = self.tlm_dict[i].nbytes

        return pkt_len_dict

    def handle(self, packet):
        """
        Params:
            packet:   message received by stream (packet)
        Returns:
            tuple of packet UID and message received by stream
        """

        # TODO validate the packet (if this is the place to do the validation)

        defined_packet_lengths = self.get_packet_lengths()

        if defined_packet_lengths[self.packet_type] != packet.nbytes:
            msg = f"PacketHandler: Packet length of packet does not match packet definition."
            raise ValueError(msg)

        return pickle.dumps((self._pkt_defn.uid, packet), 2)
