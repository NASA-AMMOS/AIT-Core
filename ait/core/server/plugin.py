from collections import defaultdict
import importlib
import re
from abc import ABCMeta, abstractmethod

import gevent
import gevent.monkey; gevent.monkey.patch_all()

import ait.core
from ait.core import  db, limits, log, notify, tlm
from client import ZMQInputClient


class Plugin(ZMQInputClient):
    """
    This is the parent class for all plugins. All plugins must implement
    their own process method which is called when a message is received.
    """

    __metaclass__ = ABCMeta

    def __init__(self, inputs, outputs, zmq_args={}, **kwargs):
        self.name = type(self).__name__
        self.inputs = inputs
        self.outputs = outputs

        for key, value in kwargs.items():
            setattr(self, key, value)

        super(Plugin, self).__init__(**zmq_args)

    def __repr__(self):
        return '<Plugin name={}>'.format(self.name)

    @abstractmethod
    def process(self, input_data, topic=None):
        pass


class DataArchive(Plugin):

    def __init__(self, inputs, outputs, datastore='ait.core.db.InfluxDBBackend', **kwargs):
        super(DataArchive, self).__init__(inputs, outputs, **kwargs)

        self.datastore = datastore
        self.packet_dict = defaultdict(dict)
        for k, v in tlm.getDefaultDict().iteritems():
            self.packet_dict[v.uid] = v

        try:
            mod, cls = self.datastore.rsplit('.', 1)
            self.dbconn = getattr(importlib.import_module(mod), cls)()
            self.dbconn.connect(**kwargs)
            log.info('Starting telemetry data archiving')
        except ImportError as e:
            log.error("Could not import specified datastore {}".format(self.datastore))
            raise(e)
        except Exception as e:
            log.error("Unable to connect to {} backend. Disabling data archive."
                        .format(self.datastore))
            raise(e)

    def process(self, input_data, topic=None, **kwargs):
        try:
            split = input_data[1:-1].split(',', 1)
            uid, pkt = int(split[0]), split[1]
            defn = self.packet_dict[uid]
            decoded = tlm.Packet(defn, data=bytearray(pkt))
            self.dbconn.insert(decoded, **kwargs)
        except Exception as e:
            log.error('Data archival failed with error: {}.'.format(e))


class TelemetryLimitMonitor(Plugin):
    def __init__(self, inputs, outputs, datastore='ait.core.db.InfluxDBBackend', **kwargs):
        super(TelemetryLimitMonitor, self).__init__(inputs, outputs, **kwargs)

        self.limit_dict = defaultdict(dict)
        for k, v in limits.getDefaultDict().iteritems():
            packet, field = k.split('.')
            self.limit_dict[packet][field] = v

        self.packet_dict = defaultdict(dict)
        for k, v in tlm.getDefaultDict().iteritems():
            self.packet_dict[v.uid] = v

        self.notif_thrshld = ait.config.get('notifications.options.threshold', 1)
        self.notif_freq = ait.config.get('notifications.options.frequency', float('inf'))

        self.limit_trip_repeats = {}
        log.info('Starting telemetry limit monitoring')

    def process(self, input_data, topic=None, **kwargs):
        split = input_data[1:-1].split(',', 1)
        pkt_id, pkt_data = int(split[0]), split[1]
        packet = self.packet_dict[pkt_id]
        decoded = tlm.Packet(packet, data=bytearray(pkt_data))

        if packet.name in self.limit_dict:
            for field, defn in self.limit_dict[packet.name].iteritems():
                v = decoded._getattr(field)

                if packet.name not in self.limit_trip_repeats.keys():
                    self.limit_trip_repeats[packet.name] = {}

                if field not in self.limit_trip_repeats[packet.name].keys():
                    self.limit_trip_repeats[packet.name][field] = 0

                if defn.error(v):
                    msg = 'Field {} error out of limit with value {}'.format(field, v)
                    log.error(msg)

                    self.limit_trip_repeats[packet.name][field] += 1
                    repeats = self.limit_trip_repeats[packet.name][field]

                    if (repeats == self.notif_thrshld or
                        (repeats > self.notif_thrshld and
                        (repeats - self.notif_thrshld) % self.notif_freq == 0)):
                        notify.trigger_notification('limit-error', msg)

                elif defn.warn(v):
                    msg = 'Field {} warning out of limit with value {}'.format(field, v)
                    log.warn(msg)

                    self.limit_trip_repeats[packet.name][field] += 1
                    repeats = self.limit_trip_repeats[packet.name][field]

                    if (repeats == self.notif_thrshld or
                        (repeats > self.notif_thrshld and
                        (repeats - self.notif_thrshld) % self.notif_freq == 0)):
                        notify.trigger_notification('limit-warn', msg)

                else:
                    self.limit_trip_repeats[packet.name][field] = 0
