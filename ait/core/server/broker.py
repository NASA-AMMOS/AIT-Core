import zmq.green as zmq
import gevent
import gevent.monkey

gevent.monkey.patch_all()

from typing import List, Any

import ait.core
import ait.core.server
from ait.core import log
from .config import ZmqConfig


class Broker(gevent.Greenlet):
    """
    This broker contains the ZeroMQ context and proxy that connects all
    streams and plugins to each other through publish-subscribe sockets.
    This broker subscribes all ZMQ clients to their input topics.
    """

    inbound_streams: List[Any] = []
    outbound_streams: List[Any] = []
    servers: List[Any] = []
    plugins: List[Any] = []

    def __init__(self):
        self.context = zmq.Context()
        self.XSUB_URL = ZmqConfig.get_xsub_url()
        self.XPUB_URL = ZmqConfig.get_xpub_url()

        # Name of the topic associated with external commands
        self.command_topic = ait.config.get("command.topic", ait.DEFAULT_CMD_TOPIC)

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
        for stream in self.inbound_streams + self.outbound_streams:
            for input_ in stream.inputs:
                if not type(input_) is int and input_ is not None:
                    Broker.subscribe(stream, input_)

        for plugin in self.plugins:
            for input_ in plugin.inputs:
                Broker.subscribe(plugin, input_)

            for output in plugin.outputs:
                # Find output stream instance
                subscriber = next(
                    (x for x in self.outbound_streams if x.name == output), None
                )
                if subscriber is None:
                    log.warn(
                        f"The outbound stream {output} does not "
                        "exist so will not receive messages "
                        f"from {plugin}")
                else:
                    Broker.subscribe(subscriber, plugin.name)

        # Lastly setup the outputstream to receive commands
        self._subscribe_cmdr()

    def _subscribe_cmdr(self):
        """
        Setup for the appropriate outbound stream that is configured to
        accept command messages.  If no stream is specified, it looks
        for the first outbound stream.
        """

        # If command topic was not supplied, report error and return
        # Technically "shouldn't happen" but better to be safe.
        if not self.command_topic:
            log.error(
                "Cannot create entry point for command subscriber, "
                "required topic name is missing."
            )
            return

        cmd_sub_flag_field = "cmd_subscriber"
        cmd_stream = None

        # Lookup for outbound stream with subscribe flag set
        cmd_streams = list(
            (
                x
                for x in self.outbound_streams
                if hasattr(x, cmd_sub_flag_field) and getattr(x, cmd_sub_flag_field)
            )
        )

        cmd_stream = next(iter(cmd_streams), None)

        # Warn about multiple matches
        if cmd_stream is not None and len(cmd_streams) > 1:
            log.warn(
                f"Multiple output streams found with {cmd_sub_flag_field} "
                f"field enabled, {cmd_stream.name} was selected as the "
                "default.")

        # No stream yet, so just grab the first output stream
        if cmd_stream is None:
            cmd_stream = next((x for x in self.outbound_streams), None)
            if cmd_stream is not None:
                log.warn("No output stream was designated as the command "
                         f"subscriber, {cmd_stream.name} was selected as "
                         "the default.")

        if cmd_stream is not None:
            Broker.subscribe(cmd_stream, self.command_topic)
        else:
            log.warn(
                "No output stream was designated as the command subscriber. "
                "Commands from other processes will not be dispatched by "
                "the server."
            )

    def subscribe_to_output(self, output_name, topic_name):
        """
        Performs a lookup for an output stream by name and if found,
        subscribes it to the publisher topic name.  Otherwise a warning
        is logged that output stream could not be found.

        Params:
            output_name: Subscriber/output name
            topic_name: Publisher/topic name

        Returns:
            True if lookup and subscription were successful, False otherwise
        """

        # Search for output stream instance by name
        subscriber = next(
            (x for x in self.outbound_streams if
             x.name == output_name), None
        )
        if subscriber is None:
            log.warn(
                f"The outbound stream {output_name} does not "
                "exist so will not receive messages "
                f"from {topic_name}")
            return False
        else:
            # Finally, setup the output stream's subscription
            # to the topic name
            Broker.subscribe(subscriber, topic_name)
            return True

    @staticmethod
    def subscribe(subscriber, publisher):
        """
        Sets subscriber's socket option to include the publisher as topic.

        Args:
            subscriber: ZMQInputClient with subscription socket
            publisher: Object whose str() method returns its associated topic
        """
        log.info(f"Subscribing {subscriber} to topic {publisher}")
        subscriber.sub.setsockopt_string(zmq.SUBSCRIBE, str(publisher))
