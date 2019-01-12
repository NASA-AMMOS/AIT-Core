from .client import Client


class Plugin(Client):

    def __init__(self, name, inputs, zmq_context,
                 broker_xpub, broker_xsub):
        self.name = name
        self.inputs = inputs

        super(Plugin, self).__init__(zmq_context, broker_xpub, broker_xsub)

