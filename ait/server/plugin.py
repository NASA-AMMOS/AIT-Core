from client import Client


class Plugin(Client):

    def __init__(self, name, **kwargs):
        super(Plugin, self).__init__()

        self.name = name
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return '<Plugin name=%s>' % (self.name)

    def process(self, input_data, topic=None):
        raise NotImplementedError((
            'This process method must be implemented by a custom plugin class ' +
            'that inherits from this abstract plugin. This abstract Plugin ' +
            'class should not be instantiated. This process method will be '
            'called whenever a message is received by the plugin.'))
