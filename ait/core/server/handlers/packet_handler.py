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
        self.packet = kwargs.get("packet", None)

        if not self.packet:
            msg = 'PacketHandler: No packet name provided in handler config as key "packet"'
            raise ValueError(msg)

        tlm_dict = tlm.getDefaultDict()
        if self.packet not in tlm_dict:
            msg = "PacketHandler: Packet name {} not present in telemetry dictionary".format(
                self.packet
            )
            msg += " Available packet types are {}".format(tlm_dict.keys())
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
