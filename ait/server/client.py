import zmq.green as zmq
import gevent
import gevent.monkey; gevent.monkey.patch_all()

import ait
from ait.core import log


class Client(gevent.Greenlet):

    def __init__(self, zmq_args=None):
        if zmq_args is None:
            zmq_args = {'context': ait.broker.context,
                        'XSUB_URL': ait.broker.XSUB_URL,
                        'XPUB_URL': ait.broker.XPUB_URL}

        self.context = zmq_args['context']
        # open PUB and SUB socket
        self.pub = self.context.socket(zmq.PUB)
        self.sub = self.context.socket(zmq.SUB)
        # connect to broker
        self.sub.connect(zmq_args['XPUB_URL'].replace('*', 'localhost'))
        self.pub.connect(zmq_args['XSUB_URL'].replace('*', 'localhost'))

        gevent.Greenlet.__init__(self)

    def _run(self):
        try:
            log.info('{} {} open to recieving messages'.format(self.type,
                                                               self.name))
            while True:
                gevent.sleep(0)
                string = self.sub.recv()
                topic, messagedata = string.split()
                log.info('%s %s recieved message \"%s\" from %s'
                         % (self.type, self.name, messagedata, topic))
                self.process(messagedata, topic=topic)

        except Exception as e:
            log.error('Exception raised in %s %s while receiving messages: %s'
                        % (self.type, self.name, e))
            raise(e)

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
