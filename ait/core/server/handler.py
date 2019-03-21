from abc import ABCMeta, abstractmethod
import cPickle as pickle

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
            ValuError:    If packet is not present in kwargs.
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
