import sys
import zmq
import ait.core
from ait.core import cfg, log
from stream import Stream


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
            frontend = self.context.socket(zmq.XSUB)
            frontend.bind(self.XSUB_URL)

            backend = self.context.socket(zmq.XPUB)
            backend.bind(self.XPUB_URL)

            zmq.proxy(frontend, backend)

        except Exception as e:
            log.error('ZeroMQ Error: %s' % e)
            raise(e)

        finally:
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
                        strm = self.create_stream(config, config_path, stream_type)
                        if stream_type == 'inbound':
                            self.inbound_streams.append(strm)
                        elif stream_type == 'outbound':
                            self.outbound_streams.append(strm)
                        log.info('Added %s stream %s' % (stream_type, strm))
                    except Exception:
                        exc_type, value, traceback = sys.exc_info()
                        log.error('%s creating stream at %s: %s' % (exc_type, config_path, value))

        if not self.inbound_streams:
            msg  = 'No valid inbound telemetry stream configurations found.'
            log.warn(msg + '  ' + error_msg['inbound'])

        if not self.outbound_streams:
            msg  = 'No valid outbound telemetry stream configurations found.'
            log.warn(msg + '  ' + error_msg['outbound'])

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
        if name in [x.name for x in (self.outbound_streams +
                                     self.inbound_streams +
                                     self.plugins)]:
            raise ValueError('Stream name already exists. Please rename.')

        stream_input = config.get('input', None)
        if stream_input is None:
            msg = cfg.AitConfigMissing(config_path + '.input').args[0]
            raise ValueError(msg)

        handlers = config.get('handlers', None)

        return Stream(name, stream_input, handlers,
                      self.context, self.XPUB_URL, self.XSUB_URL)

    def subscribe_streams(self):
        for stream in (self.inbound_streams + self.outbound_streams):
            self.subscribe(stream, stream.input_)

    def subscribe(self, subscriber, publisher):
        subscriber.sub.setsockopt(zmq.SUBSCRIBE, str(publisher))
        log.info('Subscribed %s to topic %s' % (subscriber, publisher))


# Create a singleton Broker accessible via ait.server.broker
sys.modules['ait'].broker = AitBroker()
