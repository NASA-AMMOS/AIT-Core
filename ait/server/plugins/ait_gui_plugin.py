from ait.server.plugin import Plugin


class AitGuiPlugin(Plugin):

    def __init__(self, inputs, zmq_args=None, **kwargs):
        super(AitGuiPlugin, self).__init__(inputs, zmq_args, **kwargs)

        # do something with kwargs

    def execute(self):
        # implement here
        pass
