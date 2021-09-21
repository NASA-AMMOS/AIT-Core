from abc import ABCMeta, abstractmethod


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
        return "<handler.%s>" % (self.__class__.__name__)

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
