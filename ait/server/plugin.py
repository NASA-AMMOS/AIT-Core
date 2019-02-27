import gevent
import gevent.monkey; gevent.monkey.patch_all()

from client import ZMQInputClient


class Plugin(ZMQInputClient):
    """
    This is the parent class for all plugins. All plugins must implement
    their own process method which is called when a message is received.
    """

    def __init__(self, inputs, zmq_args={}, **kwargs):
        self.type = 'Plugin'
        self.name = type(self).__name__
        self.inputs = inputs

        for key, value in kwargs.items():
            setattr(self, key, value)

        super(Plugin, self).__init__(**zmq_args)

    def __repr__(self):
        return '<Plugin name={}>'.format(self.name)

    def process(self, input_data, topic=None):
        raise NotImplementedError((
            'This process method must be implemented by a custom plugin class '
            'that inherits from this abstract plugin. This abstract Plugin '
            'class should not be instantiated. This process method will be '
            'called whenever a message is received by the plugin.'))
