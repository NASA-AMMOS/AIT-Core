import gevent.monkey
import gevent.server as gs
import gevent.socket

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
        if "listener" in kwargs and isinstance(kwargs["listener"], int):
            kwargs["listener"] = "127.0.0.1:" + str(kwargs["listener"])
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


class TCPInputServer(ZMQClient, gs.StreamServer):
    """
    This class is similar to PortInputClient except its TCP instead of UDP.
    """

    def __init__(
        self,
        zmq_context,
        zmq_proxy_xsub_url=ait.SERVER_DEFAULT_XSUB_URL,
        zmq_proxy_xpub_url=ait.SERVER_DEFAULT_XPUB_URL,
        buffer=1024,
        **kwargs,
    ):
        self.cur_socket = None
        self.buffer = buffer
        if "input" in kwargs:
            if (
                type(kwargs["input"]) not in [tuple, list]
                or kwargs["input"][0].lower() != "server"
                or type(kwargs["input"][1]) != int
            ):
                raise (
                    ValueError(
                        "TCPInputServer input must be tuple|list of (str,int) e.g. ('server',1234)"
                    )
                )

            self.sub = gevent.socket.socket(
                gevent.socket.AF_INET, gevent.socket.SOCK_STREAM
            )
            super(TCPInputServer, self).__init__(
                zmq_context,
                zmq_proxy_xsub_url,
                zmq_proxy_xpub_url,
                listener=("127.0.0.1", kwargs["input"][1]),
            )
        else:
            raise (
                ValueError(
                    "TCPInputServer input must be tuple|list of (str,int) e.g. ('server',1234)"
                )
            )

    def handle(self, socket, address):
        self.cur_socket = socket
        with socket:
            while True:
                data = socket.recv(self.buffer)
                if not data:
                    break
                log.debug("{} received message from port {}".format(self, address))
                self.process(data)


class TCPInputClient(ZMQClient):
    """
    This class creates a TCP input client.  Unlike TCPInputServer and PortInputClient,
    this class will proactively initiate a connection with an input source and begin
    receiving data from that source.  This class does not inherit directly from gevent
    servers and thus implements its own housekeeping functions.  It also implements a
    start function that spawns a process to stay consistent with the behavior of
    TCPInputServer and PortInputClient.

    """

    def __init__(
        self,
        zmq_context,
        zmq_proxy_xsub_url=ait.SERVER_DEFAULT_XSUB_URL,
        zmq_proxy_xpub_url=ait.SERVER_DEFAULT_XPUB_URL,
        connection_reattempts=5,
        buffer=1024,
        **kwargs,
    ):
        self.connection_reattempts = connection_reattempts
        self.buffer = buffer
        self.connection_status = -1
        self.proc = None

        if "buffer" in kwargs and type(kwargs["buffer"]) == int:
            self.buffer = kwargs["buffer"]

        if "input" in kwargs:
            super(TCPInputClient, self).__init__(
                zmq_context, zmq_proxy_xsub_url, zmq_proxy_xpub_url
            )
            if (
                type(kwargs["input"]) not in [tuple, list]
                or type(kwargs["input"][0]) != str
                or type(kwargs["input"][1]) != int
            ):
                raise (
                    ValueError(
                        "TCPInputClient 'input' must be tuple|list of (str,int) e.g. ('127.0.0.1',1234)"
                    )
                )
            self.sub = gevent.socket.socket(
                gevent.socket.AF_INET, gevent.socket.SOCK_STREAM
            )

            self.host = kwargs["input"][0]
            self.port = kwargs["input"][1]
            self.address = tuple(kwargs["input"])

        else:
            raise (
                ValueError(
                    "TCPInputClient 'input' must be tuple of (str,int) e.g. ('127.0.0.1',1234)"
                )
            )

    def __exit__(self):
        try:
            if self.sub:
                self.sub.close()
            if self.proc:
                self.proc.kill()
        except Exception as e:
            log.error(e)

    def __del__(self):
        try:
            if self.sub:
                self.sub.close()
            if self.proc:
                self.proc.kill()
        except Exception as e:
            log.error(e)

    def __repr__(self):
        return "<%s at %s %s>" % (
            type(self).__name__,
            hex(id(self)),
            self._formatinfo(),
        )

    def __str__(self):
        return "<%s %s>" % (type(self).__name__, self._formatinfo())

    def start(self):
        self.proc = gevent.spawn(self._client).join()

    def _connect(self):
        while self.connection_reattempts:
            try:
                res = self.sub.connect_ex((self.host, self.port))
                if res == 0:
                    self.connection_reattempts = 5
                    return res
                else:
                    self.connection_reattempts -= 1
                    gevent.sleep(1)
            except Exception as e:
                log.error(e)
                self.connection_reattempts -= 1
                gevent.sleep(1)

    def _exit(self):
        try:
            if self.sub:
                self.sub.close()
            if self.proc:
                self.proc.kill()
        except Exception as e:
            log.error(e)

    def _client(self):
        self.connection_status = self._connect()
        if self.connection_status != 0:
            log.error(
                f"Unable to connect to client: {self.address[0]}:{self.address[1]}"
            )
            self._exit()
        while True:
            packet = self.sub.recv(self.buffer)
            if not packet:
                gevent.sleep(1)
                log.info(
                    f"Trying to reconnect to client: {self.address[0]}:{self.address[1]}"
                )
                if self._connect() != 0:
                    log.error(
                        f"Unable to connect to client: {self.address[0]}:{self.address[1]}"
                    )
                    self._exit()
            self.process(packet)

    def _formatinfo(self):
        result = ""
        try:
            if isinstance(self.address, tuple) and len(self.address) == 2:
                result += "address=%s:%s" % self.address
            else:
                result += "address=%s" % (self.address,)
        except Exception as ex:
            result += str(ex) or "<error>"
        return result
