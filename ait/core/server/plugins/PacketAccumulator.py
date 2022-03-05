from ait.core.server.plugins import Plugin
from gevent import Greenlet, sleep


class PacketAccumulator(Plugin):
    def __init__(self, inputs=None, outputs=None, zmq_args=None, timer_seconds=1, max_size_octets=1024):
        super().__init__(inputs, outputs, zmq_args)

        self.packet_queue = []
        self.size_packet_queue_octets = 0

        self.glet = Greenlet.spawn(self.periodic_check)

        if timer_seconds > 0:
            self.timer_seconds = timer_seconds
        else:
            msg = f"PacketAccumulator -> timer value {timer_seconds} must be greater "
            msg += "than or equal to 0! Defaulting to 1 second."
            self.timer_seconds = 1
            self.log.error(msg)

        if max_size_octets > 0:
            self.max_size_octets = max_size_octets
        else:
            msg = f"PacketAccumulator -> Maximum accumulation size {max_size_octets} octets must "
            msg += "be greater than 0! Defaulting to 1024 octets."
            self.max_size_octets = 1024
            self.log.error(msg)

    def periodic_check(self):
        while True:
            sleep(self.timer_seconds)
            self.emit()

    def process(self, data, topic=None):
        data_len = len(data)
        # Does not fit, need to emit
        if self.size_packet_queue_octets + data_len > self.max_size_octets:
            self.emit()
        # It fits! Add and defer emission
        self.packet_queue.append(data)
        self.size_packet_queue_octets += data_len

    def emit(self):
        if self.packet_queue:
            payload = self.packet_queue.pop(0)
            for i in self.packet_queue:
                payload += i
            self.publish(payload)
            self.size_packet_queue_octets = 0
            self.packet_queue.clear()
