import gevent
import gevent.monkey; gevent.monkey.patch_all()
from importlib import import_module
import sys

# import ait
import ait.core.server
from .stream import PortInputStream, ZMQStream, PortOutputStream
from .broker import Broker
from ait.core import log, cfg
import copy

class Server(object):
    """
    This server reads and parses config.yaml to create all streams, plugins and handlers
    specified. It starts all greenlets that run these components and calls on the broker
    to manage the ZeroMQ connections.
    """
    inbound_streams = [ ]
    outbound_streams = [ ]
    servers = [ ]
    plugins = [ ]

    def __init__(self):
        self.broker = Broker()

        self._load_streams()
        self._load_plugins()

        self.broker.inbound_streams = self.inbound_streams
        self.broker.outbound_streams = self.outbound_streams
        self.broker.servers = self.servers
        self.broker.plugins = self.plugins

        # defining greenlets that need to be joined over
        self.greenlets = ([self.broker] +
                           self.broker.plugins +
                           self.broker.inbound_streams +
                           self.broker.outbound_streams)

    def wait(self):
        """
        Starts all greenlets for concurrent processing.
        Joins over all greenlets that are not servers.
        """
        for greenlet in (self.greenlets + self.servers):
            log.info("Starting {} greenlet...".format(greenlet))
            greenlet.start()

        gevent.joinall(self.greenlets)

    def _load_streams(self):
        """
        Reads, parses and creates streams specified in config.yaml.
        """
        common_err_msg = 'No valid {} stream configurations found. '
        specific_err_msg = {'inbound': 'No data will be received (or displayed).',
                            'outbound': 'No data will be published.'}
        err_msgs = {}

        for stream_type in ['inbound', 'outbound']:
            err_msgs[stream_type] = common_err_msg.format(stream_type) + specific_err_msg[stream_type]
            streams = ait.config.get('server.{}-streams'.format(stream_type))

            if streams is None:
                log.warn(err_msgs[stream_type])
            else:
                for index, s in enumerate(streams):
                    try:
                        if stream_type == 'inbound':
                            strm = self._create_inbound_stream(s['stream'])
                            if type(strm) == PortInputStream:
                                self.servers.append(strm)
                            else:
                                self.inbound_streams.append(strm)
                        elif stream_type == 'outbound':
                            strm = self._create_outbound_stream(s['stream'])
                            self.outbound_streams.append(strm)
                        log.info('Added {} stream {}'.format(stream_type, strm))
                    except Exception:
                        exc_type, value, tb = sys.exc_info()
                        log.error('{} creating {} stream {}: {}'.format(exc_type,
                                                                        stream_type,
                                                                        index,
                                                                        value))
        if not self.inbound_streams and not self.servers:
            log.warn(err_msgs['inbound'])

        if not self.outbound_streams:
            log.warn(err_msgs['outbound'])

    def _get_stream_name(self, config):
        name = config.get('name', None)
        if name is None:
            raise(cfg.AitConfigMissing('stream name'))
        if name in [x.name for x in (self.outbound_streams +
                                     self.inbound_streams +
                                     self.servers +
                                     self.plugins)]:
            raise ValueError('Duplicate stream name "{}" encountered. '
                             'Stream names must be unique.'.format(name))

        return name

    def _get_stream_handlers(self, config, name):
        stream_handlers = [ ]
        if 'handlers' in config:
            if config['handlers'] is not None:
                for handler in config['handlers']:
                    hndlr = self._create_handler(handler)
                    stream_handlers.append(hndlr)
                    log.info('Created handler {} for stream {}'.format(type(hndlr).__name__,
                                                                       name))
        else:
            log.warn('No handlers specified for stream {}'.format(name))

        return stream_handlers

    def _create_inbound_stream(self, config=None):
        """
        Creates an inbound stream from its config.

        Params:
            config:       stream configuration as read by ait.config
        Returns:
            stream:       a Stream
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if config is None:
            raise ValueError('No stream config to create stream from.')

        name = self._get_stream_name(config)
        stream_handlers = self._get_stream_handlers(config, name)
        stream_input = config.get('input', None)
        if stream_input is None:
            raise(cfg.AitConfigMissing('inbound stream {}\'s input'.format(name)))

        if type(stream_input[0]) is int:
            return PortInputStream(name,
                                   stream_input,
                                   stream_handlers,
                                   zmq_args={'zmq_context': self.broker.context,
                                             'zmq_proxy_xsub_url': self.broker.XSUB_URL,
                                             'zmq_proxy_xpub_url': self.broker.XPUB_URL})
        else:
            return ZMQStream(name,
                             stream_input,
                             stream_handlers,
                             zmq_args={'zmq_context': self.broker.context,
                                       'zmq_proxy_xsub_url': self.broker.XSUB_URL,
                                       'zmq_proxy_xpub_url': self.broker.XPUB_URL})

    def _create_outbound_stream(self, config=None):
        """
        Creates an outbound stream from its config.

        Params:
            config:       stream configuration as read by ait.config
        Returns:
            stream:       a Stream
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if config is None:
            raise ValueError('No stream config to create stream from.')

        name = self._get_stream_name(config)
        stream_handlers = self._get_stream_handlers(config, name)
        stream_input = config.get('input', None)
        stream_output = config.get('output', None)

        stream_cmd_sub = config.get('command-subscriber', None)
        if stream_cmd_sub:
            stream_cmd_sub = str(stream_cmd_sub).lower() in ['true', 'enabled', '1']

        ostream = None

        if type(stream_output) is int:
            ostream = PortOutputStream(name,
                                    stream_input,
                                    stream_output,
                                    stream_handlers,
                                    zmq_args={'zmq_context': self.broker.context,
                                              'zmq_proxy_xsub_url': self.broker.XSUB_URL,
                                              'zmq_proxy_xpub_url': self.broker.XPUB_URL})
        else:
            if stream_output is not None:
                log.warn("Output of stream {} is not an integer port. "
                         "Stream outputs can only be ports.".format(name))
            ostream = ZMQStream(name,
                             stream_input,
                             stream_handlers,
                             zmq_args={'zmq_context': self.broker.context,
                                       'zmq_proxy_xsub_url': self.broker.XSUB_URL,
                                       'zmq_proxy_xpub_url': self.broker.XPUB_URL})

        #Set the cmd subscriber field for the stream
        ostream.cmd_subscriber = stream_cmd_sub is True

        return ostream

    def _create_handler(self, config):
        """
        Creates a handler from its config.

        Params:
            config:      handler config
        Returns:
            handler instance
        """
        if config is None:
            raise ValueError('No handler config to create handler from.')

        if 'name' not in config:
            raise ValueError('Handler name is required.')

        handler_name = config['name']
        # try to create handler
        module_name = handler_name.rsplit('.', 1)[0]
        class_name = handler_name.rsplit('.', 1)[-1]
        module = import_module(module_name)
        handler_class = getattr(module, class_name)
        instance = handler_class(**config)

        return instance

    def _load_plugins(self):
        """
        Reads, parses and creates plugins specified in config.yaml.
        """
        plugins = ait.config.get('server.plugins')

        if plugins is None:
            log.warn('No plugins specified in config.')
        else:
            for index, p in enumerate(plugins):
                try:
                    plugin = self._create_plugin(p['plugin'])
                    self.plugins.append(plugin)
                    log.info('Added plugin {}'.format(plugin))

                except Exception:
                    exc_type, value, tb = sys.exc_info()
                    log.error('{} creating plugin {}: {}'.format(exc_type,
                                                                 index,
                                                                 value))
            if not self.plugins:
                log.warn('No valid plugin configurations found. No plugins will be added.')

    def _create_plugin(self, config):
        """
        Creates a plugin from its config.

        Params:
            config:       plugin configuration as read by ait.config
        Returns:
            plugin:       a Plugin
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if config is None:
            raise ValueError('No plugin config to create plugin from.')

        other_args = copy.deepcopy(config)

        name = other_args.pop('name', None)
        if name is None:
            raise(cfg.AitConfigMissing('plugin name'))

        # TODO I don't think we actually care about this being unique? Left over from
        # previous conversations about stuff?
        module_name = name.rsplit('.', 1)[0]
        class_name = name.rsplit('.', 1)[-1]
        if class_name in [x.name for x in (self.outbound_streams +
                                           self.inbound_streams +
                                           self.servers +
                                           self.plugins)]:
            raise ValueError(
                'Plugin "{}" already loaded. Only one plugin of a given name is allowed'.
                format(class_name)
            )

        plugin_inputs = other_args.pop('inputs', None)
        if plugin_inputs is None:
            log.warn('No plugin inputs specified for {}'.format(name))
            plugin_inputs = [ ]

        subscribers = other_args.pop('outputs', None)
        if subscribers is None:
            log.warn('No plugin outputs specified for {}'.format(name))
            subscribers = [ ]

        # try to create plugin
        module = import_module(module_name)
        plugin_class = getattr(module, class_name)
        instance = plugin_class(plugin_inputs,
                                subscribers,
                                zmq_args={'zmq_context': self.broker.context,
                                          'zmq_proxy_xsub_url': self.broker.XSUB_URL,
                                          'zmq_proxy_xpub_url': self.broker.XPUB_URL},
                                **other_args
        )

        return instance
