import pickle

from ait.core.server.handler import Handler
from ait.core import tlm, log


class PacketHandler(Handler):
    def __init__(self, input_type=None, output_type=None, **kwargs):
        """
        This handler provides a way to accept multiple packet types
        (e.g. '1553_HS_Packet' and 'Ethernet_HS_Packet') single stream
        and have them be processed. This handler takes a string of
        raw binary data containing the packet data.  It gets the UID from
        the telemetry dictionary.  A tuple of the UID and user data
        field is returned.

        Params:
            input_type:   (optional) Specifies expected input type, used to
                                     validate handler workflow. Defaults to None.
            output_type:  (optional) Specifies expected output type, used to
                                     validate handler workflow. Defaults to None
            **kwargs:
                packet:   (required) Type of packet (e.g. '1553_HS_Packet', 'Ethernet_HS_Packet')
                               Present in default tlm dict.
        Raises:
            ValueError:    If packet type is not present in kwargs.
                           If packet is specified but not present in default tlm dict.
     """
        super(PacketHandler, self).__init__(input_type, output_type)
        self.packet_name = kwargs.get("packet", None)
        self.tlm_dict = tlm.getDefaultDict()

        if not self.packet_name:
            msg = f'PacketHandler: No packet type provided in handler config as key {self.packet_name}'
            raise ValueError(msg)

        if self.packet_name not in self.tlm_dict:
            msg = f"PacketHandler: Packet name '{self.packet_name}' not present in telemetry dictionary."
            msg += f" Available packet types are {self.tlm_dict.keys()}"
            raise ValueError(msg)

        self._pkt_defn = self.tlm_dict[self.packet_name]

    def handle(self, input_data):
        """
        Test the input_data length against the length in the telemetry

        Params:
            input_data :  byteArray
                message received by stream (raw data)
        Returns:
            tuple of packet UID and message received by stream
        """

        if self._pkt_defn.nbytes != len(input_data):
            log.error(
                f"PacketHandler: Packet data length does not match packet definition."
            )
            return 0
        else:
            return pickle.dumps((self._pkt_defn.uid, input_data), 2)

        return pickle.dumps((self._pkt_defn.uid, input_data), 2)
