import zmq
import ait
from ait.core import log
from threading import Thread


class Client(object):

    def __init__(self):
        self.context = ait.broker.context

        # open PUB and SUB socket
        self.pub = self.context.socket(zmq.PUB)
        self.sub = self.context.socket(zmq.SUB)
        # connect to broker
        self.sub.connect(ait.broker.XPUB_URL.replace('*', 'localhost'))
        self.pub.connect(ait.broker.XSUB_URL.replace('*', 'localhost'))

        # start receiving messages
        thread = Thread(target=self.recv, args=())
        thread.daemon = True
        thread.start()

    def recv(self):
        try:
            log.info('%s %s open to recieving messages'
                      % (type(self).__name__, self.name))
            while True:
                string = self.sub.recv()
                topic, messagedata = string.split()
                log.info('%s %s recieved message \"%s\" from %s'
                         % (type(self).__name__, self.name, messagedata, topic))
                self.process(messagedata, topic=topic)

        except Exception as e:
            log.error('Exception raised in %s %s while receiving messages: %s'
                        % (type(self).__name__, self.name, e))
            raise(e)

    def publish(self, msg):
        """
        Publish specified message with client name as topic.
        """
        self.pub.send("%s %s" % (self.name, msg))
        log.info('Published message %s from %s %s'
                   % (msg, type(self).__name__, self.name))

    def process(self, input_data, topic=None):
        """ Called whenever a message is received """
        raise(NotImplementedError('This method must be implemented in all '
                                  'subclasses of Client.'))
