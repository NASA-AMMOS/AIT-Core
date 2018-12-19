import sys
import zmq
import ait.core
from ait.core import cfg, log
from stream import (InboundStream, OutboundStream)


class AitBroker:
    XSUB_URL = "tcp://*:5559"
    XPUB_URL = "tcp://*:5560"

    def __init__(self):
        self.inbound_streams = [ ]
        self.outbound_streams = [ ]
        self.ports = [ ]
        self.plugins = [ ]

        self.context = zmq.Context()

        self.load_streams()
        self.subscribe_streams()
        self.start_broker()

    def start_broker(self):
        try:
            # Socket facing clients
            frontend = self.context.socket(zmq.XSUB)
            frontend.bind(self.XSUB_URL)

            # Socket facing services
            backend = self.context.socket(zmq.XPUB)
            backend.bind(self.XPUB_URL)

            zmq.proxy(frontend, backend)

        except Exception as e:
            log.error('ZeroMQ Error: %s' % e)

        finally:
            # We never get here...
            frontend.close()
            backend.close()
            self.context.term()

    def load_streams(self):
        error_msg = {'inbound': 'No telemetry will be received (or displayed).',
                     'outbound': 'No telemetry will be published.'}

        for stream_type in ['inbound', 'outbound']:
            streams = ait.config.get('server.%s-streams' % stream_type)

            if streams is None:
                msg = cfg.AitConfigMissing('server.%s-streams' % stream_type).args[0]
                log.error(msg + '  ' + error_msg[stream_type])
            else:
                for index, s in enumerate(streams):
                    try:
                        config_path = 'server.%s-streams[%d].stream' % (stream_type, index)
                        config = cfg.AitConfig(config=s).get('stream')
                        strm = self.create_stream(config, config_path, stream_type=stream_type)
                        if stream_type == 'inbound':
                            self.inbound_streams.append(strm)
                        elif stream_type == 'outbound':
                            self.outbound_streams.append(strm)
                        log.info('Added %s stream %s' % (stream_type, strm))
                    except Exception as e:
                        log.error(e)

            if not self.inbound_streams:
                msg  = 'No valid inbound telemetry stream configurations found.'
                log.warn(msg + '  ' + error_msg[stream_type])

            if not self.outbound_streams:
                msg  = 'No valid outbound telemetry stream configurations found.'
                log.warn(msg + '  ' + error_msg[stream_type])

    def create_stream(self, config, config_path, stream_type):
        """
        Creates a stream from its config.

        Params:
            config:       stream configuration as read by ait.config
            config_path:  string path to stream's yaml config
            stream_type:  either 'inbound' or 'outbound'
        Returns:
            stream:       either an OutboundStream() or an InboundStream()
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if stream_type not in ['inbound', 'outbound']:
            raise ValueError('Stream type must be \'inbound\' or \'outbound\'.')

        if config is None:
            msg = cfg.AitConfigMissing(config_path).args[0]
            raise ValueError(msg)

        name = config.get('name', None)
        if name is None:
            msg = cfg.AitConfigMissing(config_path + '.name').args[0]
            raise ValueError(msg)

        stream_input = config.get('input', None)
        if stream_input is None:
            msg = cfg.AitConfigMissing(config_path + '.input').args[0]
            raise ValueError(msg)

        # determine input type
        if stream_type == 'outbound':
            # look for name in plugins, then streams
            if stream_input in self.plugins:
                input_type = 'plugin'
            elif stream_input in self.streams:
                input_type = 'stream'

        if stream_type == 'inbound':
            # check if input is port by attempting conversion to int;
            # otherwise stream
            try:
                stream_input = int(stream_input)
                input_type = 'port'
            except ValueError:
                input_type = 'stream'

        handlers = config.get('handlers', None)

        if stream_type == 'outbound':
            return OutboundStream(name, stream_input, input_type, handlers,
                                  self.context, self.XPUB_URL, self.XSUB_URL)
        if stream_type == 'inbound':
            return InboundStream(name, stream_input, input_type, handlers,
                                 self.context, self.XPUB_URL, self.XSUB_URL)

    def subscribe_streams(self):
        for stream in (self.inbound_streams + self.outbound_streams):
            if stream.input_type == 'port':
                port = stream.input_
                # renaming Servers to Ports
                if port not in self.ports:
                    self.ports.append(port)
                # subscribe to it
                topicfilter = ""
                stream.sub.setsockopt(zmq.SUBSCRIBE, topicfilter)

            elif stream.input_type == 'stream':
                input_stream = stream.input_
                # check if stream already created?
                # if not, create it??
                # subscribe to it
                topicfilter = ""
                stream.sub.setsockopt(zmq.SUBSCRIBE, topicfilter)

            elif stream.input_type == 'plugin':
                plugin = stream.input_
                # check if plugin registered with broker
                # if not register it
                # subscribe to it
                topicfilter = ""
                stream.sub.setsockopt(zmq.SUBSCRIBE, topicfilter)

    def subscribe(self, subscriber, publisher):
        pass


# Create a singleton Broker accessible via ait.server.broker
sys.modules['ait'].broker = AitBroker()
