from .client import Client


class Plugin(Client):

    def __init__(self, name, inputs):
        self.name = name
        self.inputs = inputs

        self.start_greenlet()

        super(Plugin, self).__init__()

    def start_greenlet(self):
        pass


class ExamplePlugin(Plugin):

    def __init__(self, name, inputs, **kwargs):
        super(ExamplePlugin, self).__init__(name, inputs)
