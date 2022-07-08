import gevent
import gevent.monkey

from importlib import import_module
import sys
import traceback

import ait.core.server
from .stream import PortInputStream, ZMQStream, PortOutputStream
from .config import ZmqConfig
from .broker import Broker
from .plugin import PluginType, Plugin, PluginConfig
from .process import PluginsProcess
from ait.core import log, cfg

gevent.monkey.patch_all()


class Server(object):
    """
    This server reads and parses config.yaml to create all streams, plugins and handlers
    specified. It starts all greenlets and processes that run these components and calls
    on the broker to manage the ZeroMQ connections.
    """

    def __init__(self):
        self.broker = Broker()

        self.inbound_streams = []
        self.outbound_streams = []
        self.servers = []
        self.plugins = []

        # Dict from process namespace to PluginsProcess
        self.plugin_process_dict = {}

        self._load_streams_and_plugins()

        # list of plugin processes that will be spawned
        self.plugin_processes = self.plugin_process_dict.values()

        self.broker.inbound_streams = self.inbound_streams
        self.broker.outbound_streams = self.outbound_streams
        self.broker.servers = self.servers
        self.broker.plugins = self.plugins

        # defining greenlets that need to be joined over
        self.greenlets = (
            [self.broker]
            + self.broker.plugins
            + self.broker.inbound_streams
            + self.broker.outbound_streams
        )

    def wait(self):
        """
        Starts all greenlets and plugin-pocesses for concurrent processing.
        Joins over all greenlets that are not servers.
        """
        # Start all of the greenlets managed by this process
        for greenlet in self.greenlets + self.servers:
            log.info(f"Starting {greenlet} greenlet...")
            greenlet.start()

        # Start all of the separate plugin processes
        for plugin_process in self.plugin_processes:
            log.info(f"Spawning {plugin_process} process...")
            plugin_process.spawn_process()

        # Subscribe process-plugin output streams to plugin names
        self._subscribe_process_plugins_outputs()

        gevent.joinall(self.greenlets)

    def _subscribe_process_plugins_outputs(self):
        """
        While each PluginsProcess performs its own subscription setup for
        input streams as part of its process spin-up, setting up the output
        stream connections is handled here.

        The reason is we need to access the underlying subscription socket
        of the output streams, which are all running in the original server
        process.
        """

        for plugin_process in self.plugin_processes:
            plugin_outputs_dict = plugin_process.get_plugin_outputs()
            for plugin_name in plugin_outputs_dict.keys():
                for output_name in plugin_outputs_dict.get(plugin_name):
                    self.broker.subscribe_to_output(output_name, plugin_name)

    def _load_streams_and_plugins(self):
        """
        Load collection of streams and plugins.
        """
        self._load_streams()
        self._create_api_telem_stream()
        self._load_plugins()

    def _load_streams(self):
        """
        Reads, parses and creates streams specified in config.yaml.
        """
        common_err_msg = "No valid {} stream configurations found. "
        specific_err_msg = {
            "inbound": "No data will be received (or displayed).",
            "outbound": "No data will be published.",
        }
        err_msgs = {}

        for stream_type in ["inbound", "outbound"]:
            err_msgs[stream_type] = (
                common_err_msg.format(stream_type) + specific_err_msg[stream_type]
            )
            streams = ait.config.get(f"server.{stream_type}-streams")

            if streams is None:
                log.warn(err_msgs[stream_type])
            else:
                for index, s in enumerate(streams):
                    try:
                        if stream_type == "inbound":
                            strm = self._create_inbound_stream(s["stream"])
                            if type(strm) == PortInputStream:
                                self.servers.append(strm)
                            else:
                                self.inbound_streams.append(strm)
                        elif stream_type == "outbound":
                            strm = self._create_outbound_stream(s["stream"])
                            self.outbound_streams.append(strm)
                        log.info(f"Added {stream_type} stream {strm}")
                    except Exception:
                        exc_type, value, tb = sys.exc_info()
                        log.error(f"{exc_type} creating {stream_type} stream "
                                  f"{index}: {value}")
        if not self.inbound_streams and not self.servers:
            log.warn(err_msgs["inbound"])

        if not self.outbound_streams:
            log.warn(err_msgs["outbound"])

    def _create_api_telem_stream(self):
        """"""
        stream_map = {"__valid_api_streams": []}
        compatible_handlers = ["PacketHandler", "CCSDSPacketHandler"]

        streams = ait.config.get("server.inbound-streams", None)
        if streams is None:
            log.warn("Unable to setup API telemetry stream. No streams are configured")
            return

        for stream in streams:
            stream = stream["stream"]
            stream_map[stream["name"]] = stream

            # If the last handler that runs in a stream is one of our
            # compatible_handlers we count it as a valid API telemetry stream.
            # Users should use the config options for an explicit and less
            # restrictive list.
            if (
                "handlers" in stream
                and stream["handlers"][-1]["name"].split(".")[-1] in compatible_handlers
            ):
                stream_map["__valid_api_streams"].append(stream["name"])
                continue

        # Pull API stream config and process as necessary. If no config is set
        # we need to default to our list of valid API streams (if possible).
        config_streams = ait.config.get("server.api-telemetry-streams", [])

        if not isinstance(config_streams, list):
            log.error(
                "server.api-telemetry-streams configuration is unexpected type "
                f"{type(config_streams)} instead of list of stream names. "
            )
            config_streams = []

        if len(config_streams) == 0:
            log.warn(
                "No configuration found for API Streams. Attempting to determine "
                "valid streams to use as default."
            )

            if len(stream_map["__valid_api_streams"]) == 0:
                log.warn("Unable to find valid streams to use as API defaults.")
            else:
                log.info(
                    "Located potentially valid streams. "
                    f"{stream_map['__valid_api_streams']} uses a compatible handler "
                    f"({compatible_handlers})."
                )
                config_streams = stream_map["__valid_api_streams"]

        streams = []
        for stream in config_streams:
            if stream not in stream_map:
                log.warn(f"Invalid stream name {stream}. Skipping ...")
            else:
                streams.append(stream)

        if len(streams) > 0:
            tlm_api_topic = ait.config.get("telemetry.topic", ait.DEFAULT_TLM_TOPIC)
            self.inbound_streams.append(
                self._create_inbound_stream({"name": tlm_api_topic, "input": streams})
            )
        else:
            log.error(
                "No streams available for telemetry API. Ground scripts API "
                "functionality will not work."
            )

    def _get_stream_name(self, config):
        name = config.get("name", None)
        if name is None:
            raise (cfg.AitConfigMissing("stream name"))
        if name in [
            x.name
            for x in (
                self.outbound_streams
                + self.inbound_streams
                + self.servers
                + self.plugins
            )
        ]:
            raise ValueError(f"Duplicate stream name '{name}' encountered. "
                             "Stream names must be unique.")

        return name

    def _get_stream_handlers(self, config, name):
        stream_handlers = []
        if "handlers" in config:
            if config["handlers"] is not None:
                for handler in config["handlers"]:
                    hndlr = self._create_handler(handler)
                    stream_handlers.append(hndlr)
                    log.info(f"Created handler {type(hndlr).__name__} for "
                             f"stream {name}")
        else:
            log.warn(f"No handlers specified for stream {name}")

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
            raise ValueError("No stream config to create stream from.")

        name = self._get_stream_name(config)
        stream_handlers = self._get_stream_handlers(config, name)
        stream_input = config.get("input", None)
        if stream_input is None:
            raise (cfg.AitConfigMissing(f"inbound stream {name}'s input"))

        # Create ZMQ args re-using the Broker's context
        zmq_args_dict = self._create_zmq_args(True)

        if type(stream_input[0]) is int:
            return PortInputStream(
                name,
                stream_input,
                stream_handlers,
                zmq_args=zmq_args_dict,
            )
        else:
            return ZMQStream(
                name,
                stream_input,
                stream_handlers,
                zmq_args=zmq_args_dict,
            )

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
            raise ValueError("No stream config to create stream from.")

        name = self._get_stream_name(config)
        stream_handlers = self._get_stream_handlers(config, name)
        stream_input = config.get("input", None)
        stream_output = config.get("output", None)

        stream_cmd_sub = config.get("command-subscriber", None)
        if stream_cmd_sub:
            stream_cmd_sub = str(stream_cmd_sub).lower() in ["true", "enabled", "1"]

        ostream = None

        # Create ZMQ args re-using the Broker's context
        zmq_args_dict = self._create_zmq_args(True)

        if type(stream_output) is int:
            ostream = PortOutputStream(
                name,
                stream_input,
                stream_output,
                stream_handlers,
                zmq_args=zmq_args_dict,
            )
        else:
            if stream_output is not None:
                log.warn(f"Output of stream {name} is not an integer port. "
                         "Stream outputs can only be ports.")
            ostream = ZMQStream(
                name,
                stream_input,
                stream_handlers,
                zmq_args=zmq_args_dict,
            )

        # Set the cmd subscriber field for the stream
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
            raise ValueError("No handler config to create handler from.")

        if "name" not in config:
            raise ValueError("Handler name is required.")

        handler_name = config["name"]
        # try to create handler
        module_name = handler_name.rsplit(".", 1)[0]
        class_name = handler_name.rsplit(".", 1)[-1]
        module = import_module(module_name)
        handler_class = getattr(module, class_name)
        instance = handler_class(**config)

        return instance

    def _load_plugins(self):
        """
        Reads, parses and creates plugins specified in config.yaml.

        Plugins with no process namespace will be instantiated.

        Plugins associated with a process namespace however will
        have its configuration parsed and prepared for later instantiation
        (during child-process creation).
        """
        plugins = ait.config.get("server.plugins")

        if plugins is None:
            log.warn("No plugins specified in config.")
        else:
            for index, p in enumerate(plugins):
                ait_cfg_plugin = p["plugin"]

                # If a plugin config includes a 'process_id' entry, then
                # that indicates that plugin will run in a separate process
                # with that id.  Multiple plugins can specify the same value
                # which allows them to all run within a process together
                process_namespace = ait_cfg_plugin.pop('process_id', None)
                plugin_type = PluginType.STANDARD if process_namespace is \
                    None else PluginType.PROCESS

                if plugin_type == PluginType.PROCESS:

                    # Plugin will run in a separate process (possibly with other
                    # plugins)

                    try:
                        # Check if the namespace has already been created
                        plugins_process = self.plugin_process_dict.get(
                                          process_namespace, None)

                        # If not, then create it and add to managed dict
                        if plugins_process is None:
                            plugins_process = PluginsProcess(process_namespace)
                            self.plugin_process_dict[process_namespace] = \
                                plugins_process

                        # Convert ait config section to PluginConfig instance
                        plugin_info = self._create_plugin_info(ait_cfg_plugin,
                                                               False)

                        # If successful, then add it to the process
                        if plugin_info is not None:
                            plugins_process.add_plugin_info(plugin_info)
                            log.info("Added config for deferred plugin "
                                     f"{plugin_info.name} to plugin-process "
                                     f"'{process_namespace}'")

                    except Exception:
                        exc_type, exc_msg, tb = sys.exc_info()
                        log.error(f"{exc_type} creating plugin config {index} "
                                  f"for process-id '{process_namespace}': "
                                  f"{exc_msg}")
                        log.error(traceback.format_exc())

                else:

                    # Plugin will run in current process's greenlet set
                    try:
                        plugin = self._create_plugin(ait_cfg_plugin)
                        if plugin is not None:
                            self.plugins.append(plugin)
                            log.info(f"Added plugin {plugin}")

                    except Exception:
                        exc_type, value, tb = sys.exc_info()
                        log.error(f"{exc_type} creating plugin {index}: "
                                  f"{value}")

            if not self.plugins and not self.plugin_process_dict:
                log.warn("No valid plugin configurations found. No plugins"
                         " will be added.")

    def _create_zmq_args(self, reuse_broker_context):
        """
        Creates a dict of ZMQ arguments needed for Plugins.

        Params:
            reuse_broker_context:   Flag indicating if context is shared from
                 Broker.  If False, then None is used for value.
        Returns:
            A dictionary of ZeroMQ connection arguments
        """
        zmq_ctxt = self.broker.context if reuse_broker_context else None
        zmq_args = {
            "zmq_context": zmq_ctxt,
            "zmq_proxy_xsub_url": ZmqConfig.get_xsub_url(),
            "zmq_proxy_xpub_url": ZmqConfig.get_xpub_url(),
        }
        return zmq_args

    def _create_plugin(self, ait_plugin_config):
        """
        Creates a plugin from its config.

        Params:
            ait_plugin_config:  plugin configuration as read by ait.config
        Returns:
            plugin:       a Plugin
        Raises:
            ValueError:   if any of the required config values are missing
        """

        # Create PluginConfig instance, re-use the Broker's ZMQ Context
        plugin_info = self._create_plugin_info(ait_plugin_config, True)

        # Create the Plugin instance
        plugin = Plugin.create_plugin(plugin_info)

        return plugin

    def _create_plugin_info(self, ait_plugin_config, reuse_broker_context):
        """
        Creates a plugin-specific config from AIT config.

        Params:
            ait_plugin_config: plugin configuration as read by ait.config
        Returns:
            plugin:       a PluginConfig instance
        Raises:
            ValueError:   if any of the required config values are missing
        """
        if ait_plugin_config is None:
            raise ValueError("No plugin config to create plugin from.")

        # Create ZMQ args re-using the Broker's context
        zmq_args = self._create_zmq_args(reuse_broker_context)

        # Create Plugin config (which checks for required args)
        plugin_config = PluginConfig.build_from_ait_config(ait_plugin_config,
                                                           zmq_args)

        return plugin_config
