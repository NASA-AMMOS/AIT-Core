from collections import defaultdict
import importlib
import re
from abc import ABCMeta, abstractmethod

import gevent
import gevent.monkey; gevent.monkey.patch_all()

import ait.core
from ait.core import  db, limits, log, notify, tlm
from client import ZMQInputClient
import cPickle as pickle


class Plugin(ZMQInputClient):
    """
    This is the parent class for all plugins. All plugins must implement
    their own process method which is called when a message is received.
    """

    __metaclass__ = ABCMeta

    def __init__(self, inputs, outputs, zmq_args={}, **kwargs):
        """
        Params:
            inputs:     names of inbound streams plugin receives data from
            outputs:    names of outbound streams plugin sends its data to
            zmq_args:   dict containing the follow keys:
                            zmq_context
                            zmq_proxy_xsub_url
                            zmq_proxy_xpub_url
                        Defaults to empty dict. Default values
                        assigned during instantiation of parent class.
            **kwargs:   (optional) Dependent on requirements of child class.
        """
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
        """
        Not implemented by base Plugin class.
        This process method must be implemented by any custom plugin class
        that inherits from this base Plugin.

        Params:
            input_data:  Message received from any of the plugin's input streams.
            topic:       Name of stream that message was received from.
        """
        pass


class DataArchive(Plugin):

    def __init__(self, inputs, outputs, datastore='ait.core.db.InfluxDBBackend', **kwargs):
        """
        Attempts to connect to database backend. Plugin will not be created if
        connection fails.

        Creates base packet dictionary for decoding packets with packet UIDs as
        keys and packet definitions as values.

        Params:
            inputs:      list of names of input streams to plugin
            outputs:     list of names of plugin output streams
            datastore:   path to database backend to use
            **kwargs:    any args required for connecting to backend database
        Raises:
            ImportError:   raised if provided database backend does not exist or
                           cannot be imported
            Exception:     raised if the backened database cannot be connected to
                           for any reason
        """
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
        """
        Splits tuple received from PacketHandler into packet UID and packet message.
        Decodes packet and inserts into database backend.
        Logs any exceptions raised.

        Params:
            input_data:  message received from inbound stream through PacketHandler
            topic:       name of inbound stream message received from
            **kwargs:    any args required for connected to the backend
        """
        try:
            load = pickle.loads(input_data)
            uid, pkt = int(load[0]), load[1]
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
        try:
            load = pickle.loads(input_data)
            pkt_id, pkt_data = int(load[0]), load[1]
            packet = self.packet_dict[pkt_id]
            decoded = tlm.Packet(packet, data=bytearray(pkt_data))
        except Exception as e:
            log.error('TelemetryLimitMonitor: {}'.format(e))
            log.error('TelemetryLimitMonitor received input_data that it is unable to process. Skipping input ...')
            return

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
