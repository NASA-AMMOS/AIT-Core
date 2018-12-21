import zmq


class Stream(object):
    STR_INPUT_TYPE = [ ]

    def __init__(self, name, input_, handlers,
                       zmq_context, broker_xpub, broker_xsub):
        self.name = name
        self.input_ = input_
        self.handlers = handlers
        self.context = zmq_context

        if not self.valid_workflow():
            raise ValueError('Sequential workflow inputs and outputs ' +
                             'are not compatible. Workflow is invalid.')

        # open PUB and SUB socket
        self.pub = self.context.socket(zmq.PUB)
        self.sub = self.context.socket(zmq.SUB)
        # connect to broker
        self.sub.connect(broker_xpub.replace('*', 'localhost'))
        self.pub.connect(broker_xsub.replace('*', 'localhost'))

    def _type(self):
        return self.__class__.__name__.split('Stream')[0].lower()

    def __repr__(self):
        return '<Stream name=%s>' % (self.name)

    def publish(self, msg):
        """
        Publish specified message with stream name as topic.
        """
        self.pub.send("%d %d" % (self.name, msg))

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
