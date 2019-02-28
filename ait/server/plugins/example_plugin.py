from ait.server.plugin import Plugin


class ExamplePlugin(Plugin):

    def __init__(self, inputs, outputs, **kwargs):
        super(ExamplePlugin, self).__init__(inputs, outputs, **kwargs)

        # do something here if desired

    def process(self):
        # implement here
        pass
