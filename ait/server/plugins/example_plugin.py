from ait.server.plugin import Plugin


class ExamplePlugin(Plugin):

    def __init__(self, name, **kwargs):
        super(ExamplePlugin, self).__init__(name, **kwargs)

        # do something here if desired

    def process(self):
        # implement here
        pass
