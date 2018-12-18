import ait.core
from ait.core import cfg


class Stream(object):
    STR_INPUT_TYPE = [ ]

    def __init__(self, name, input_, input_type, handlers):
        # determine input type
        self.name = name
        self.input_type = input_type
        self.input_ = input_
        self.handlers = handlers

    def _type(self):
        return self.__class__.__name__.split('Stream')[0].lower()

    def __repr__(self):
        return '<stream.%s name=%s>' % (self.__class__.__name__, self.name)

    def publish(self):
        pass

    def validate_workflow(self):
        pass


class InboundStream(Stream):
    STR_INPUT_TYPE = ['stream']

    def __init__(self, name, input_, input_type, handlers):
        super(InboundStream, self).__init__(name, input_, input_type, handlers)


class OutboundStream(Stream):
    STR_INPUT_TYPE = ['plugin', 'stream']

    def __init__(self, name, input_, input_type, handlers):
        super(OutboundStream, self).__init__(name, input_, input_type, handlers)
