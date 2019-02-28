from collections import defaultdict
import importlib
import gevent
import re

from ait.server.plugin import Plugin
from ait.core import tlm, log, db


class DataArchivalPlugin(Plugin):

    def __init__(self, inputs, outputs, datastore='ait.core.db.InfluxDBBackend', **kwargs):
        super(DataArchivalPlugin, self).__init__(inputs, outputs, **kwargs)

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
