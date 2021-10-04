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

import gevent
import gevent.monkey

gevent.monkey.patch_all()

import ait.core
from ait.core import limits, log, notify, tlm
from ait.core.server.plugin import Plugin


class TelemetryLimitMonitor(Plugin):
    def __init__(self, inputs, outputs, **kwargs):
        super(TelemetryLimitMonitor, self).__init__(inputs, outputs, **kwargs)

        self.limit_dict = defaultdict(dict)
        for k, v in limits.getDefaultDict().items():
            packet, field = k.split(".")
            self.limit_dict[packet][field] = v

        self.packet_dict = defaultdict(dict)
        for _k, v in tlm.getDefaultDict().items():
            self.packet_dict[v.uid] = v

        self.notif_thrshld = ait.config.get("notifications.options.threshold", 1)
        self.notif_freq = ait.config.get(
            "notifications.options.frequency", float("inf")
        )

        self.limit_trip_repeats = {}
        log.info("Starting telemetry limit monitoring")

    def process(self, input_data, topic=None, **kwargs):
        try:
            load = pickle.loads(input_data)
            pkt_id, pkt_data = int(load[0]), load[1]
            packet = self.packet_dict[pkt_id]
            decoded = tlm.Packet(packet, data=bytearray(pkt_data))
        except Exception as e:
            log.error("TelemetryLimitMonitor: {}".format(e))
            log.error(
                "TelemetryLimitMonitor received input_data that it is unable to process. Skipping input ..."
            )
            return

        if packet.name in self.limit_dict:
            for field, defn in self.limit_dict[packet.name].items():
                v = decoded._getattr(field)

                if packet.name not in self.limit_trip_repeats.keys():
                    self.limit_trip_repeats[packet.name] = {}

                if field not in self.limit_trip_repeats[packet.name].keys():
                    self.limit_trip_repeats[packet.name][field] = 0

                if defn.error(v):
                    msg = "Field {} error out of limit with value {}".format(field, v)
                    log.error(msg)

                    self.limit_trip_repeats[packet.name][field] += 1
                    repeats = self.limit_trip_repeats[packet.name][field]

                    if repeats == self.notif_thrshld or (
                        repeats > self.notif_thrshld
                        and (repeats - self.notif_thrshld) % self.notif_freq == 0
                    ):
                        notify.trigger_notification("limit-error", msg)

                elif defn.warn(v):
                    msg = "Field {} warning out of limit with value {}".format(field, v)
                    log.warn(msg)

                    self.limit_trip_repeats[packet.name][field] += 1
                    repeats = self.limit_trip_repeats[packet.name][field]

                    if repeats == self.notif_thrshld or (
                        repeats > self.notif_thrshld
                        and (repeats - self.notif_thrshld) % self.notif_freq == 0
                    ):
                        notify.trigger_notification("limit-warn", msg)

                else:
                    self.limit_trip_repeats[packet.name][field] = 0
