# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2019, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

from collections import defaultdict
import pickle
import importlib

import gevent
import gevent.monkey

gevent.monkey.patch_all()

import ait.core  # noqa
from ait.core import log, tlm
from ait.core.server.plugin import Plugin


class DataArchive(Plugin):
    def __init__(
        self, inputs, outputs, datastore="ait.core.db.InfluxDBBackend", **kwargs
    ):
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
        for _k, v in tlm.getDefaultDict().items():
            self.packet_dict[v.uid] = v

        try:
            mod, cls = self.datastore.rsplit(".", 1)
            self.dbconn = getattr(importlib.import_module(mod), cls)()
            self.dbconn.connect(**kwargs)
            log.info("Starting telemetry data archiving")
        except ImportError as e:
            log.error("Could not import specified datastore {}".format(self.datastore))
            raise (e)
        except Exception as e:
            log.error(
                "Unable to connect to {} backend. Disabling data archive.".format(
                    self.datastore
                )
            )
            raise (e)

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
            log.error("Data archival failed with error: {}.".format(e))
