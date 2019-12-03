import zmq.green as zmq
import gevent
import gevent.monkey; gevent.monkey.patch_all()

import ait.core
import ait.core.server
from ait.core import log


class Broker(gevent.Greenlet):
    """
    This broker contains the ZeroMQ context and proxy that connects all
    streams and plugins to each other through publish-subscribe sockets.
    This broker subscribes all ZMQ clients to their input topics.
    """
    inbound_streams = [ ]
    outbound_streams = [ ]
    servers = [ ]
    plugins = [ ]

    def __init__(self):
        self.context = zmq.Context()
        self.XSUB_URL = ait.config.get('server.xsub',
                                        ait.SERVER_DEFAULT_XSUB_URL)
        self.XPUB_URL = ait.config.get('server.xpub',
                                        ait.SERVER_DEFAULT_XPUB_URL)

        gevent.Greenlet.__init__(self)

    def _run(self):
        self._setup_proxy()
        self._subscribe_all()

        log.info("Starting broker...")
        while True:
            gevent.sleep(0)
            socks = dict(self.poller.poll())

            if socks.get(self.frontend) == zmq.POLLIN:
                message = self.frontend.recv_multipart()
                self.backend.send_multipart(message)

            if socks.get(self.backend) == zmq.POLLIN:
                message = self.backend.recv_multipart()
                self.frontend.send_multipart(message)

    def _setup_proxy(self):
        self.frontend = self.context.socket(zmq.XSUB)
        self.frontend.bind(self.XSUB_URL)

        self.backend = self.context.socket(zmq.XPUB)
        self.backend.bind(self.XPUB_URL)

        self.poller = zmq.Poller()
        self.poller.register(self.frontend, zmq.POLLIN)
        self.poller.register(self.backend, zmq.POLLIN)

    def _subscribe_all(self):
        """
        Subscribes all streams to their input.
        Subscribes all plugins to all their inputs.
        Subscribes all plugin outputs to the plugin.
        """
        for stream in (self.inbound_streams + self.outbound_streams):
            for input_ in stream.inputs:
                if not type(input_) is int and input_ is not None:
                    self._subscribe(stream, input_)

        for plugin in self.plugins:
            for input_ in plugin.inputs:
                self._subscribe(plugin, input_)

            for output in plugin.outputs:
                # Find output stream instance
                subscriber = next((x for x in self.outbound_streams
                                  if x.name == output), None)
                if subscriber is None:
                    log.warn('The outbound stream {} does not '
                             'exist so will not receive messages '
                             'from {}'.format(output, plugin))
                else:
                    self._subscribe(subscriber, plugin.name)

    def _subscribe(self, subscriber, publisher):
        log.info('Subscribing {} to topic {}'.format(subscriber, publisher))
        subscriber.sub.setsockopt_string(zmq.SUBSCRIBE, str(publisher))
