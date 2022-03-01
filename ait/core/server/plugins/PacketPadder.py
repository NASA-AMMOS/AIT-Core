from ait.core.server.plugins import Plugin
from ait.core import log


class PacketPadder(Plugin):
    def __init__(self, inputs=None, outputs=None, zmq_args=None, pad_octets=0, **kwargs):
        if pad_octets >= 0:
            self.size_pad_octets = pad_octets
        else:
            self.size_pad_octets = 0
            log.error(f"PacketPadder -> Pad value{pad_octets} octets must be a \
                        positive integer! Bypassing padding!")
        super().__init__(inputs, outputs, zmq_args)

    def process(self, data, topic=None):
        if len(data) < self.size_pad_octets:
            fill = bytearray(self.size_pad_octets - len(data))
            data = data + fill
        self.publish(data)
