from collections import defaultdict
import importlib
import re

import gevent
import gevent.monkey; gevent.monkey.patch_all()

from ait.core import tlm, log, db
from client import ZMQInputClient


class Plugin(ZMQInputClient):
    """
    This is the parent class for all plugins. All plugins must implement
    their own process method which is called when a message is received.
    """

    def __init__(self, inputs, outputs, zmq_args={}, **kwargs):
        self.type = 'Plugin'
        self.name = type(self).__name__
        self.inputs = inputs
        self.outputs = outputs

        for key, value in kwargs.items():
            setattr(self, key, value)

        super(Plugin, self).__init__(**zmq_args)

    def __repr__(self):
        return '<Plugin name={}>'.format(self.name)

    def process(self, input_data, topic=None):
        raise NotImplementedError((
            'This process method must be implemented by a custom plugin class '
            'that inherits from this abstract plugin. This abstract Plugin '
            'class should not be instantiated. This process method will be '
            'called whenever a message is received by the plugin.'))


class DataArchive(Plugin):

    def __init__(self, inputs, outputs, datastore='ait.core.db.InfluxDBBackend', **kwargs):
        super(DataArchive, self).__init__(inputs, outputs, **kwargs)

        self.datastore = datastore

    def process(self, input_data, topic=None, **kwargs):
        packet_dict = defaultdict(dict)
        for k, v in tlm.getDefaultDict().iteritems():
            packet_dict[v.uid] = v

        try:
            mod, cls = self.datastore.rsplit('.', 1)
            dbconn = getattr(importlib.import_module(mod), cls)()
            dbconn.connect(**kwargs)
        except ImportError:
            log.error("Could not import specified datastore {}".format(self.datastore))
            return
        except Exception as e:
            log.error("Unable to connect to InfluxDB backend. Disabling data archive.\n{}".format(e))
            return

        try:
            log.info('Starting telemetry data archiving')
            split = re.split(r'\((\d),(\'.*\')\)', input_data)
            uid, pkt = int(split[1]), split[2]
            defn = packet_dict[uid]
            decoded = tlm.Packet(defn, data=bytearray(pkt))
            dbconn.insert(decoded, **kwargs)

            gevent.sleep(0)
        finally:
            dbconn.close()
            log.info('Telemetry data archiving terminated')
