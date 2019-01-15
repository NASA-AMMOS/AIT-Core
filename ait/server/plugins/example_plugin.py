from ait.server.plugin import Plugin


class ExamplePlugin(Plugin):

    def __init__(self, name, inputs, **kwargs):
        super(ExamplePlugin, self).__init__(name, inputs)

        # do something with kwargs

    def execute(self):
        # implement here
        pass
