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
        self.packet_name = kwargs.get("packet", None)
        self.tlm_dict = tlm.getDefaultDict()

        if not self.packet_name:
            msg = f'PacketHandler: No packet type provided in handler config as key "packet"'
            raise ValueError(msg)

        if self.packet_name not in self.tlm_dict:
            msg = f"PacketHandler: Packet name '{self.packet_name}' not present in telemetry dictionary."
            msg += f" Available packet types are {self.tlm_dict.keys()}"
            raise ValueError(msg)

        self._pkt_defn = self.tlm_dict[self.packet_name]

    def handle(self, packet):
        """
        Params:
            packet:   message received by stream (packet)
        Returns:
            tuple of packet UID and message received by stream
        """

        if self._pkt_defn.nbytes != packet.nbytes:
            msg = f"PacketHandler: Packet length of packet does not match packet definition."
            raise ValueError(msg)

        return pickle.dumps((self._pkt_defn.uid, packet), 2)
