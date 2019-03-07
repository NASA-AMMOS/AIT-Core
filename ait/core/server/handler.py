from abc import ABCMeta, abstractmethod

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
        """
        pass


class PacketHandler(Handler):

    def __init__(self, input_type=None, output_type=None, **kwargs):
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
        # this is being published to ZMQ - needs to work
        return (self._pkt_defn.uid, input_data)
