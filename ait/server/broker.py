import sys
import zmq.green as zmq
import gevent
import gevent.monkey; gevent.monkey.patch_all()
from importlib import import_module

import ait.core
import ait.server
from ait.core import cfg, log
from stream import Stream


class AitBroker(gevent.Greenlet):

    def __init__(self):

        self.inbound_streams = [ ]
        self.outbound_streams = [ ]
        self.ports = [ ]
        self.plugins = [ ]

        self.context = zmq.Context()
        self.XSUB_URL = ait.config.get('server.xsub',
                                        ait.server.DEFAULT_XSUB_URL)
        self.XPUB_URL = ait.config.get('server.xpub',
                                        ait.server.DEFAULT_XPUB_URL)

        self.load_streams()
        self.load_plugins()
        self.subscribe_all()

        gevent.Greenlet.__init__(self)

    def _run(self):
        try:
            frontend = self.context.socket(zmq.XSUB)
            frontend.bind(self.XSUB_URL)

            backend = self.context.socket(zmq.XPUB)
            backend.bind(self.XPUB_URL)

            log.info('Starting up broker...')
            zmq.proxy(frontend, backend)
            print("Started broker")

        except Exception as e:
            log.error('ZeroMQ Error: {}'.format(e))
            raise(e)

        finally:
            frontend.close()
            backend.close()
            self.context.term()

    def load_streams(self):
        common_err_msg = 'No valid {} telemetry stream configurations found. '
        specific_err_msg = {'inbound': 'No telemetry will be received (or displayed).',
                            'outbound': 'No telemetry will be published.'}
        err_msgs = {}

        for stream_type in ['inbound', 'outbound']:
            err_msgs[stream_type] = common_err_msg.format(stream_type) + specific_err_msg[stream_type]
            streams = ait.config.get('server.{}-streams'.format(stream_type))

            if streams is None:
                log.warn(err_msgs[stream_type])
            else:
                for index, s in enumerate(streams):
                    try:
                        strm = self.create_stream(s['stream'], stream_type)
                        if stream_type == 'inbound':
                            self.inbound_streams.append(strm)
                        elif stream_type == 'outbound':
                            self.outbound_streams.append(strm)
                        log.info('Added {} stream {}'.format(stream_type, strm))
                    except Exception:
                        exc_type, value, tb = sys.exc_info()
                        log.error('{} creating {} stream {}: {}'.format(exc_type,
                                                                        stream_type,
                                                                        index,
                                                                        value))

        if not self.inbound_streams:
            log.warn(err_msgs['inbound'])

        if not self.outbound_streams:
            log.warn(err_msgs['outbound'])

    def create_stream(self, config, stream_type):
        """
        Creates a stream from its config.

        Params:
            config:       stream configuration as read by ait.config
            stream_type:  either 'inbound' or 'outbound'
        Returns:
            stream:       a Stream
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if stream_type not in ['inbound', 'outbound']:
            raise ValueError('Stream type must be \'inbound\' or \'outbound\'.')

        if config is None:
            raise ValueError('No stream config to create stream from.')

        name = config.get('name', None)
        if name is None:
            raise(cfg.AitConfigMissing(stream_type + ' stream name'))
        if name in [x.name for x in (self.outbound_streams +
                                     self.inbound_streams +
                                     self.plugins)]:
            raise ValueError('Stream name already exists. Please rename.')

        stream_input = config.get('input', None)
        if stream_input is None:
            raise(cfg.AitConfigMissing(stream_type + ' stream input'))

        stream_handlers = [ ]
        if config['handlers']:
            for handler in config['handlers']:
                hndlr = self.create_handler(handler)
                stream_handlers.append(hndlr)
                log.info('Created handler {} for stream {}'.format(type(hndlr).__name__,
                                                                   name))
        else:
            log.warn('No handlers specified for {} stream {}'.format(stream_type,
                                                                     name))

        return Stream(name,
                      stream_input,
                      stream_handlers,
                      zmq_args={'context': self.context,
                                'XSUB_URL': self.XSUB_URL,
                                'XPUB_URL': self.XPUB_URL})

    def create_handler(self, config):
        """
        Creates a handler from its config.

        Params:
            config:      handler config
        """
        if config is None:
            raise ValueError('No handler config to create handler from.')

        # check if input/output types specified
        if type(config) == str:
            handler_name = config
            input_type, output_type = None, None
        else:
            handler_name = config.keys()[0]
            input_type = config[handler_name]['input_type']
            output_type = config[handler_name]['output_type']

        # try to create handler
        class_name = handler_name.title().replace('_', '')
        module = import_module('ait.server.handlers.{}'.format(handler_name))
        handler_class = getattr(module, class_name)
        instance = handler_class(input_type, output_type)

        return instance

    def subscribe_all(self):
        for stream in (self.inbound_streams + self.outbound_streams):
            self.subscribe(stream, stream.input_)

        for plugin in self.plugins:
            for input_ in plugin.inputs:
                self.subscribe(plugin, input_)

    def subscribe(self, subscriber, publisher):
        subscriber.sub.setsockopt(zmq.SUBSCRIBE, str(publisher))
        log.info('Subscribed {} to topic {}'.format(subscriber, publisher))

    def get_stream(self, name):
        return next((strm
                     for strm in (self.inbound_streams + self.outbound_streams)
                     if strm.name == name),
                     None)

    def load_plugins(self):
        plugins = ait.config.get('server.plugins')

        if plugins is None:
            log.warn('No plugins specified in config.')
        else:
            for index, p in enumerate(plugins):
                try:
                    plugin = self.create_plugin(p['plugin'])
                    self.plugins.append(plugin)
                    log.info('Added plugin {}'.format(plugin))
                except Exception:
                    exc_type, value, tb = sys.exc_info()
                    log.error('{} creating plugin {}: {}'.format(exc_type,
                                                                 index,
                                                                 value))
            if not self.plugins:
                log.warn('No valid plugin configurations found. No plugins will be added.')

    def create_plugin(self, config):
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

        name = config.get('name', None)
        if name is None:
            raise(cfg.AitConfigMissing('plugin name'))

        class_name = name.title().replace('_', '')
        if class_name in [x.name for x in (self.outbound_streams +
                                           self.inbound_streams +
                                           self.plugins)]:
            raise ValueError('Plugin name already exists. Please rename.')

        plugin_inputs = config.get('inputs', None)
        if plugin_inputs is None:
            log.warn('No plugin inputs specified for {}'.format(name))
            plugin_inputs = [ ]

        # try to create plugin
        module = import_module('ait.server.plugins.{}'.format(name))
        plugin_class = getattr(module, class_name)
        instance = plugin_class(plugin_inputs,
                                zmq_args={'context': self.context,
                                          'XSUB_URL': self.XSUB_URL,
                                          'XPUB_URL': self.XPUB_URL})

        return instance
