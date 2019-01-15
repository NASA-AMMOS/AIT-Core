from ait.server.plugin import Plugin


class GUIPlugin(Plugin):

    def __init__(self, name, inputs, **kwargs):
        super(GUIPlugin, self).__init__(name, inputs)

        # do something with kwargs

    def execute(self):
        # implement here
        pass
