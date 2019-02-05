import gevent
import gevent.monkey; gevent.monkey.patch_all()

from client import Client
import ait


class Plugin(Client):

    def __init__(self, inputs, zmq_args=None, **kwargs):
        self.type = 'Plugin'
        self.name = type(self).__name__
        self.inputs = inputs
        for key, value in kwargs.items():
            setattr(self, key, value)

        super(Plugin, self).__init__(zmq_args)

    def __repr__(self):
        return '<Plugin name={}>'.format(self.name)

    def process_telemetry(self, input_data, topic=None):
        raise NotImplementedError((
            'This process method must be implemented by a custom plugin class '
            'that inherits from this abstract plugin. This abstract Plugin '
            'class should not be instantiated. This process method will be '
            'called whenever a message is received by the plugin.'))
