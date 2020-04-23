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

        ## Name of the topic associated with external commands
        self.command_topic = ait.config.get('command.topic',
                                        ait.DEFAULT_CMD_TOPIC)

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

        ## Lastly setup the outputstream to receive commands
        self._subscribe_cmdr()

    def _subscribe_cmdr(self):
        """
        Setup for the appropriate outbound stream that is configured to
        accept command messages.  If no stream is specified, it looks
        for the first outbound stream.
        """

        ## If command topic was not supplied, report error and return
        ## Technically "shouldn't happen" but better to be safe.
        if not self.command_topic:
            log.error('Cannot create entry point for command subscriber, '
                      'required topic name is missing.')
            return

        cmd_sub_flag_field = 'cmd_subscriber'
        cmd_stream = None

        ##Lookup for outbound stream with subscribe flag set
        cmd_streams = list((x for x in self.outbound_streams
                       if hasattr(x, cmd_sub_flag_field) and
                       getattr(x, cmd_sub_flag_field)))

        cmd_stream = next(iter(cmd_streams), None)

        ## Warn about multiple matches
        if cmd_stream and len(cmd_streams) > 1:
            log.warn('Multiple output streams found with {} field enabled, '
                     '{} was selected as the default.'.format(
                     cmd_sub_flag_field, cmd_stream.name))


        ## No stream yet, so just grab the first output stream
        if not cmd_stream:
            cmd_stream = next((x for x in self.outbound_streams), None)
            if cmd_stream:
                log.warn('No output stream was designated as the command subscriber, '
                         '{} was selected as the default.'.format(cmd_stream.name) )

        if cmd_stream:
            self._subscribe(cmd_stream, self.command_topic)
        else:
            log.warn('No output stream was designated as the command subscriber. '
                     'Commands from other processes will not be dispatched by the server.')


    def _subscribe(self, subscriber, publisher):
        log.info('Subscribing {} to topic {}'.format(subscriber, publisher))
        subscriber.sub.setsockopt_string(zmq.SUBSCRIBE, str(publisher))
