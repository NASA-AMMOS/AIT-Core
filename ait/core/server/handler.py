import __builtin__

from ait.core import log, tlm


class Handler(object):
    """
    This is the base Handler class that all custom handlers must inherit
    from. All custom handlers must implement the handle method, which will
    called by the stream the handler is attached to when the stream receives
    data.
    """

    def __init__(self, input_type=None, output_type=None, **kwargs):
        self.input_type = input_type
        self.output_type = output_type

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return '<handler.%s>' % (self.__class__.__name__)

    def validate_input(self, input_data):
        """
        Attempts to convert input data to expected input type, if specified.
        If no input type specified, returns input data.
        If conversion fails, raises Exception.
        If conversion successful, returns converted data.
        """
        if self.input_type:
            try:
                converted = getattr(__builtin__,
                                    self.input_type.decode())(input_data)
            except Exception as e:
                raise(e)

            return converted

        return input_data

    def execute_handler(self, input_data):
        """
        Checks that the input data to the handler matches the expected
        input type. If input data is of the correct type, calls the
        handle method. If input data is not the correct type, raises a
        ValueError.
        """
        try:
            checked_input = self.validate_input(input_data)
        except Exception as e:
            raise(ValueError('Input is not of valid type: ', e))

        return self.handle(checked_input)

    def handle(self, input_data):
        """
        Not implemented by base Handler class.
        This handle method must be implemented by any custom handler class
        that inherits from this base Handler.
        """
        raise NotImplementedError((
            'This handle method must be implemented by a custom handler class ' +
            'that inherits from this abstract Handler. This abstract Handler ' +
            'class should not be instantiated.'))


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


class CcsdsPacketHandler(Handler):

    def __init__(self, input_type, output_type=None):
        super(CcsdsPacketHandler, self).__init__(input_type, output_type)

    def handle(self, input_data):
        return input_data + 5


class TmTransFrameDecodeHandler(Handler):

    def __init__(self, input_type, output_type=None):
        super(TmTransFrameDecodeHandler, self).__init__(input_type, output_type)

    def handle(self, input_data):
        return input_data + 5
