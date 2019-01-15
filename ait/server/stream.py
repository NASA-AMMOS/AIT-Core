import ait.server.broker
from client import Client


class Stream(Client):

    def __init__(self, name, input_, handlers):
        self.name = name
        self.input_ = input_
        self.handlers = handlers

        if not self.valid_workflow():
            raise ValueError('Sequential workflow inputs and outputs ' +
                             'are not compatible. Workflow is invalid.')

        super(Stream, self).__init__()

    def _type(self):
        if self in ait.broker.inbound_streams:
            return 'inbound'
        elif self in ait.broker.outbound_streams:
            return 'outbound'
        else:
            raise(Exception('Stream %s not registered with broker.' % self.name))

    def __repr__(self):
        return '<Stream name=%s>' % (self.name)

    def process(self, input_):
        for handler in self.handlers:
            output = handler.execute_handler(input_)
            input_ = output

    def valid_workflow(self):
        """
        Return true if each handler's output type is the same as
        the next handler's input type. Return False if not.
        """
        for ix, handler in enumerate(self.handlers[:-1]):
            next_input_type = self.handlers[ix + 1].input_type

            if (handler.output_type is not None and
                    next_input_type is not None):
                if handler.output_type != next_input_type:
                    return False

        return True
