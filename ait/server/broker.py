import sys

from stream import (InboundStream, OutboundStream)

import ait.core
from ait.core import cfg, log


class AitBroker:

    def __init__(self):
        self.inbound_streams = [ ]
        self.outbound_streams = [ ]
        self.ports = [ ]
        self.plugins = [ ]

        self.load_streams()
        self.subscribe_streams()

    def load_streams(self):
        inbound_streams = ait.config.get('server.inbound-streams')
        outbound_streams = ait.config.get('server.outbound-streams')

        if inbound_streams is None:
            msg = cfg.AitConfigMissing('server.inbound-streams').args[0]
            msg += '  No telemetry will be received (or displayed).'
            log.error(msg)
        else:
            for index, s in enumerate(inbound_streams):
                try:
                    strm = InboundStream(s, index)
                    self.inbound_streams.append(strm)
                    log.info('Added inbound stream %s' % strm)
                except Exception as e:
                    log.error(e)

            if outbound_streams is None:
                msg = cfg.AitConfigMissing('server.outbound-streams').args[0]
                msg += '  No telemetry will be published.'
                log.warn(msg)
            else:
                for index, s in enumerate(outbound_streams):
                    try:
                        strm = OutboundStream(s, index)
                        self.outbound_streams.append(strm)
                        log.info('Added outbound stream %s' % strm)
                    except Exception as e:
                        log.error(e)

                if not self.outbound_streams:
                    msg  = 'No valid outbound telemetry stream configurations found.'
                    msg += '  No handled telemetry will be published.'
                    log.warn(msg)

            if not self.inbound_streams:
                msg  = 'No valid inbound telemetry stream configurations found.'
                msg += '  No telemetry will be received (or displayed).'
                log.error(msg)

    def subscribe_streams(self):
        for stream in (self.inbound_streams + self.outbound_streams):
            if stream.input_type == 'port':
                port = stream.input
                # renaming Servers to Ports
                if port not in self.ports:
                    self.ports.append(port)
                # subscribe to it

            elif stream.input_type == 'stream':
                input_stream = stream.input
                # check if stream already created
                # if not, create it
                # subscribe to it
                pass

            elif stream.input_type == 'plugin':
                plugin = stream.input
                # check if plugin registered with broker
                # if not register it
                # subscribe to it
                pass

    def subscribe(self, subscriber, publisher):
        pass


# Create a singleton Broker accessible via ait.server.broker
sys.modules['ait'].broker = AitBroker()
