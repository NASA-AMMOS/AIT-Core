import gevent
import gevent.socket
import gevent.server as gs
import gevent.monkey

gevent.monkey.patch_all()

import zmq.green as zmq
import socket

import ait.core
from ait.core import log
import ait.core.server.utils as utils


class ZMQClient(object):
    """
    This is the base ZeroMQ client class that all streams and plugins
    inherit from. It opens a ZMQ PUB socket to publish messages to
    and publishes to it.
    """

    def __init__(
        self,
        zmq_context,
        zmq_proxy_xsub_url=ait.SERVER_DEFAULT_XSUB_URL,
        zmq_proxy_xpub_url=ait.SERVER_DEFAULT_XPUB_URL,
        **kwargs,
    ):

        self.context = zmq_context
        # open PUB socket & connect to broker
        self.pub = self.context.socket(zmq.PUB)
        self.pub.connect(zmq_proxy_xsub_url.replace("*", "localhost"))
        if 'listener' in kwargs and isinstance(kwargs['listener'], int) :
            kwargs['listener'] = "127.0.0.1:"+str(kwargs['listener'])
        # calls gevent.Greenlet or gs.DatagramServer __init__
        super(ZMQClient, self).__init__(**kwargs)

    def publish(self, msg, topic=None):
        """
        Publishes input message with client name as the topic if the
        topic parameter is not provided.

        Publishes input message with topic as the topic if the
        topic parameter is provided. Topic can be an arbitrary string.
        """
        if not topic:
            topic = self.name
        msg = utils.encode_message(topic, msg)
        if msg is None:
            log.error(f"{self} unable to encode msg {msg} for send.")
            return

        self.pub.send_multipart(msg)
        log.debug("Published message from {}".format(self))

    def process(self, input_data, topic=None):
        """This method must be implemented by all streams and plugins that
        inherit from ZMQClient. It is called whenever a message is received.

        Params:
            input_data:  message received by client
            topic:       name of component message received from, if received
                         through ZeroMQ
        Raises:
            NotImplementedError since not implemented in base parent class
        """
        raise (
            NotImplementedError(
                "This method must be implemented in all " "subclasses of Client."
            )
        )


class ZMQInputClient(ZMQClient, gevent.Greenlet):
    """
    This is the parent class for all streams and plugins with
    input streams. It opens a ZeroMQ SUB socket for receiving
    ZMQ messages from the input streams it is subscribed to and stays
    open to receiving those messages, calling the process method
    on all messages received.
    """

    def __init__(
        self,
        zmq_context,
        zmq_proxy_xsub_url=ait.SERVER_DEFAULT_XSUB_URL,
        zmq_proxy_xpub_url=ait.SERVER_DEFAULT_XPUB_URL,
        **kwargs,
    ):

        super(ZMQInputClient, self).__init__(
            zmq_context, zmq_proxy_xsub_url, zmq_proxy_xpub_url
        )

        self.context = zmq_context
        self.sub = self.context.socket(zmq.SUB)
        self.sub.connect(zmq_proxy_xpub_url.replace("*", "localhost"))

        gevent.Greenlet.__init__(self)

    def _run(self):
        try:
            while True:
                gevent.sleep(0)
                msg = self.sub.recv_multipart()
                topic, message = utils.decode_message(msg)
                if topic is None or message is None:
                    log.error(f"{self} received invalid topic or message. Skipping")
                    continue

                log.debug("{} received message from {}".format(self, topic))
                self.process(message, topic=topic)

        except Exception as e:
            log.error(
                "Exception raised in {} while receiving messages: {}".format(self, e)
            )
            raise (e)


class PortOutputClient(ZMQInputClient):
    """
    This is the parent class for all outbound streams which publish
    to a port. It opens a UDP port to publish to and publishes
    outgoing message data to this port.
    """

    def __init__(
        self,
        zmq_context,
        zmq_proxy_xsub_url=ait.SERVER_DEFAULT_XSUB_URL,
        zmq_proxy_xpub_url=ait.SERVER_DEFAULT_XPUB_URL,
        **kwargs,
    ):

        super(PortOutputClient, self).__init__(
            zmq_context, zmq_proxy_xsub_url, zmq_proxy_xpub_url
        )
        self.out_port = kwargs["output"]
        self.context = zmq_context
        # override pub to be udp socket
        self.pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def publish(self, msg):
        self.pub.sendto(msg, ("localhost", int(self.out_port)))
        log.debug("Published message from {}".format(self))


class PortInputClient(ZMQClient, gs.DatagramServer):
    """
    This is the parent class for all inbound streams which receive messages
    on a port. It opens a UDP port for receiving messages, listens for them,
    and calls the process method on all messages received.
    """

    def __init__(
        self,
        zmq_context,
        zmq_proxy_xsub_url=ait.SERVER_DEFAULT_XSUB_URL,
        zmq_proxy_xpub_url=ait.SERVER_DEFAULT_XPUB_URL,
        **kwargs,
    ):

        if "input" in kwargs and type(kwargs["input"][0]) is int:
            super(PortInputClient, self).__init__(
                zmq_context,
                zmq_proxy_xsub_url,
                zmq_proxy_xpub_url,
                listener=int(kwargs["input"][0]),
            )
        else:
            raise (ValueError("Input must be port in order to create PortInputClient"))

        # open sub socket
        self.sub = gevent.socket.socket(gevent.socket.AF_INET, gevent.socket.SOCK_DGRAM)

    def handle(self, packet, address):
        # This function provided for gs.DatagramServer class
        log.debug("{} received message from port {}".format(self, address))
        self.process(packet)
