from ait.core import log, tlm
from handler import Handler


class AitPacketHandler(Handler):

    def __init__(self, input_type=None, output_type=None, **kwargs):
        super(AitPacketHandler, self).__init__(input_type, output_type)
        self.packet = kwargs.get('packet', None)

        if not self.packet:
            msg = 'AITPacketHandler: No packet name provided in handler config as key "packet"'
            raise ValueError(msg)

        tlm_dict = tlm.getDefaultDict()
        if self.packet not in tlm_dict:
            msg = 'AITPacketHandler: Packet name {} not present in telemetry dictionary'.format(self.packet)
            msg += ' Available packet types are {}'.format(tlm_dict.keys())
            raise ValueError(msg)

        self._pkt_defn = tlm_dict[self.packet]

    def handle(self, input_data):
        # this is being published to ZMQ - needs to work
        return (self._pkt_defn.uid, input_data)
