import zmq


class Stream(object):
    STR_INPUT_TYPE = [ ]

    def __init__(self, name, input_, input_type, handlers,
                       zmq_context, broker_xpub, broker_xsub):
        self.name = name
        self.input_type = input_type
        self.input_ = input_
        self.handlers = handlers
        self.context = zmq_context

        # open PUB and SUB socket
        self.pub = self.context.socket(zmq.PUB)
        self.sub = self.context.socket(zmq.SUB)
        # connect to broker
        self.sub.connect(broker_xpub)
        self.pub.connect(broker_xsub)

    def _type(self):
        return self.__class__.__name__.split('Stream')[0].lower()

    def __repr__(self):
        return '<stream.%s name=%s>' % (self.__class__.__name__, self.name)

    def publish(self, msg):
        # msg topic is stream name
        self.pub.send("%d %d" % (self.name, msg))

    def validate_workflow(self):
        pass


class InboundStream(Stream):
    STR_INPUT_TYPE = ['stream']

    def __init__(self, name, input_, input_type, handlers,
                 zmq_context, broker_xpub, broker_xsub):
        super(InboundStream, self).__init__(name, input_, input_type, handlers,
                                            zmq_context, broker_xpub, broker_xsub)


class OutboundStream(Stream):
    STR_INPUT_TYPE = ['plugin', 'stream']

    def __init__(self, name, input_, input_type, handlers,
                 zmq_context, broker_xpub, broker_xsub):
        super(OutboundStream, self).__init__(name, input_, input_type, handlers,
                                             zmq_context, broker_xpub, broker_xsub)
