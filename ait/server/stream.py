import ait
from client import Client


class Stream(Client):

    def __init__(self, name, input_, handlers, zmq_args=None):
        if zmq_args is None:
            zmq_args = {'context': ait.broker.context,
                        'XSUB_URL': ait.broker.XSUB_URL,
                        'XPUB_URL': ait.broker.XPUB_URL}

        self.name = name
        self.input_ = input_
        self.handlers = handlers

        if not self.valid_workflow():
            raise ValueError('Sequential workflow inputs and outputs ' +
                             'are not compatible. Workflow is invalid.')

        super(Stream, self).__init__(zmq_args)

    @property
    def type(self):
        try:
            if self in ait.broker.inbound_streams:
                return 'Inbound Stream'
            elif self in ait.broker.outbound_streams:
                return 'Outbound Stream'
            else:
                raise(Exception('Stream %s not registered with broker.' % self.name))
        except AttributeError:
            return 'Stream'

    def __repr__(self):
        return '<Stream name=%s>' % (self.name)

    def process(self, input_data, topic=None):
        for handler in self.handlers:
            output = handler.execute_handler(input_data)
            input_data = output

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
