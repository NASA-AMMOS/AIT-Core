from client import ZMQInputClient, PortInputClient


class Stream(object):

    def __init__(self, name, input_, handlers, zmq_args={}):
        self.name = name
        self.input_ = input_
        self.handlers = handlers

        if not self.valid_workflow():
            raise ValueError('Sequential workflow inputs and outputs ' +
                             'are not compatible. Workflow is invalid.')

        # This calls __init__ on subclass of ZMQClient
        super(Stream, self).__init__(input_=self.input_, **zmq_args)

    def __repr__(self):
        return '<%s name=%s>' % (self.type, self.name)

    @property
    def type(self):
        return type(self)

    def process(self, input_data, topic=None):
        for handler in self.handlers:
            output = handler.execute_handler(input_data)
            input_data = output

        self.publish(input_data)

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


class PortInputStream(Stream, PortInputClient):

    def __init__(self, name, input_, handlers, zmq_args={}):
        super(PortInputStream, self).__init__(name, input_, handlers, zmq_args)


class ZMQInputStream(Stream, ZMQInputClient):

    def __init__(self, name, input_, handlers, zmq_args={}):
        super(ZMQInputStream, self).__init__(name, input_, handlers, zmq_args)
