import gevent
import gevent.socket
import gevent.server as gs
import gevent.monkey; gevent.monkey.patch_all()

import zmq.green as zmq

import ait
from ait.core import log


class ZMQClient(object):

    def __init__(self,
                 zmq_context,
                 zmq_proxy_xsub_url=ait.server.DEFAULT_XSUB_URL,
                 zmq_proxy_xpub_url=ait.server.DEFAULT_XPUB_URL,
                 **kwargs):

        self.context = zmq_context
        # open PUB socket & connect to broker
        self.pub = self.context.socket(zmq.PUB)
        self.pub.connect(zmq_proxy_xsub_url.replace('*', 'localhost'))

        # calls gevent.Greenlet or gs.DatagramServer __init__
        super(ZMQClient, self).__init__(**kwargs)

    def publish(self, msg):
        """
        Publish specified message with client name as topic.
        """
        self.pub.send("%s %s" % (self.name, msg))
        log.info('Published message %s from %s %s'
                   % (msg, self.type, self.name))

    def process(self, input_data, topic=None):
        """ Called whenever a message is received """
        raise(NotImplementedError('This method must be implemented in all '
                                  'subclasses of Client.'))


class ZMQInputClient(ZMQClient, gevent.Greenlet):

    def __init__(self,
                 zmq_context,
                 zmq_proxy_xsub_url=ait.server.DEFAULT_XSUB_URL,
                 zmq_proxy_xpub_url=ait.server.DEFAULT_XPUB_URL,
                 **kwargs):

        super(ZMQInputClient, self).__init__(zmq_context,
                                             zmq_proxy_xsub_url,
                                             zmq_proxy_xpub_url)

        self.context = zmq_context
        # open sub socket
        self.sub = self.context.socket(zmq.SUB)
        self.sub.connect(zmq_proxy_xpub_url.replace('*', 'localhost'))

        gevent.Greenlet.__init__(self)

    def _run(self):
        try:
            log.info('{} {} open to recieving messages'.format(self.type,
                                                               self.name))
            while True:
                gevent.sleep(0)
                string = self.sub.recv()
                print("Message recieved:", string.split())
                topic, messagedata = string.split()
                log.info('{} {} recieved message \"{}\" from {}'
                         .format(self.type, self.name, messagedata, topic))
                self.process(messagedata, topic=topic)

        except Exception as e:
            log.error('Exception raised in {} {} while receiving messages: {}'
                       .format(self.type, self.name, e))
            raise(e)


class PortInputClient(ZMQClient, gs.DatagramServer):
    def __init__(self,
                 input_,
                 zmq_context,
                 zmq_proxy_xsub_url=ait.server.DEFAULT_XSUB_URL,
                 zmq_proxy_xpub_url=ait.server.DEFAULT_XPUB_URL):

        super(PortInputClient, self).__init__(zmq_context,
                                              zmq_proxy_xsub_url,
                                              zmq_proxy_xpub_url,
                                              listener=int(input_))

        # open sub socket
        self.sub = gevent.socket.socket(gevent.socket.AF_INET, gevent.socket.SOCK_DGRAM)

    def handle(self, packet, address):
        # This function provided for gs.DatagramServer class
        log.info('{} {} recieved message \"{}\" from port {}'
                 .format(self.type, self.name, packet, address))
        self.process(packet)
