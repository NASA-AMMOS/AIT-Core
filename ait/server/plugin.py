from .client import Client
import gevent


class Plugin(Client):

    def __init__(self, name, inputs):
        self.name = name
        self.inputs = inputs

        self.start_greenlet()

        super(Plugin, self).__init__()

    def __repr__(self):
        return '<Plugin name=%s>' % (self.name)

    def start_greenlet(self):
        telem_handler = gevent.util.wrap_errors(KeyboardInterrupt, self.execute())
        # s below was a session - should be something different now
        Greenlets.append(gevent.spawn(telem_handler, s))

    def execute(self):
        raise NotImplementedError((
            'This execute method must be implemented by a custom plugin class ' +
            'that inherits from this abstract plugin. This abstract Plugin ' +
            'class should not be instantiated.'))
