from abc import ABCMeta, abstractmethod

import enum
import copy
from importlib import import_module
from ait.core import log, cfg
from .client import ZMQInputClient

import gevent.monkey
gevent.monkey.patch_all()


class PluginType(enum.Enum):
    """
    Enumeration for Plugin type: standard plugin (greenlet) or process-based
    """
    STANDARD = enum.auto()
    PROCESS = enum.auto()

    @classmethod
    def value_of(cls, str_value, default):
        """
        Class method that returns a Type enum based on string value.
        If value is None or does not match, then Type.GREENLET is returned
        by default.

        Params:
            value: Name associated with the enum
            default: Default value to be returned, can be None

        Returns:
            plugin.Type - Type enum instance
        """
        if str_value:
            for k, v in cls.__members__.items():
                if k.lower() == str_value.lower():
                    return v
        if default:
            return default
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{str_value}'")


class PluginConfig(object):
    """
    Data-structure for plugin information.
    Would be useful if we allow multiple plugins to run in a common
    child-process
    """

    def __init__(self, name, inputs=None, outputs=None, zmq_args=None, kwargs=None):
        """
        Constructor

        Params:
            name:       Name of the Plugin class (required)
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
        if name is None:
            raise (cfg.AitConfigMissing("plugin name"))

        self.name = name
        self.inputs = inputs if inputs is not None else []
        self.outputs = outputs if outputs is not None else []
        self.zmq_args = zmq_args if zmq_args is not None else {}
        self.kwargs = kwargs if kwargs is not None else {}

        self.inputs = [self.inputs] if isinstance(self.inputs, str) else self.inputs
        self.outputs = [self.inputs] if isinstance(self.inputs, str) else self.outputs

    @property
    def short_name(self):
        """
        Returns the classname portion of the fullname
        Returns: Class name of plugin type
        """
        return self.name.rsplit(".", 1)[-1]

    def get_zmq_context(self):
        """
        Convenience method that gets value of the ZMQ context

        Returns: ZMQ Context, possibly None
        """
        return self.zmq_args.get('zmq_context', None)

    def set_zmq_context(self, context):
        """
        Convenience method that gets value of the ZMQ context

        Params:
            context:    ZeroMQ Context, can be None
        """
        self.zmq_args['zmq_context'] = context

    @staticmethod
    def build_from_ait_config(ait_plugin_config, zmq_args=None):
        """
        Static method that extracts information from AIT Plugin
        configuration and returns a newly instantiated
        PluginConfig object.
        Any required configuration that is missing will result in
        error.

        Params:
            ait_plugin_config: AIT configuration section of a plugin
            zmq_args: ZMQ settings

        Returns:
            PluginConfig - New PluginConfig built from config

        Raises:
            AitConfigMissing:  if any of the required config values are missing
        """

        if zmq_args is None:
            zmq_args = {}

        # Make a copy of the config that we can manipulate
        other_args = copy.deepcopy(ait_plugin_config)

        # Extract name and ensure it is defined
        name = other_args.pop("name", None)
        if name is None:
            raise (cfg.AitConfigMissing("plugin name"))

        plugin_inputs = other_args.pop("inputs", None)
        if plugin_inputs is None:
            log.warn(f"No plugin inputs specified for {name}")
            plugin_inputs = []

        subscribers = other_args.pop("outputs", None)
        if subscribers is None:
            log.warn(f"No plugin outputs specified for {name}")
            subscribers = []

        plugin_config = PluginConfig(name, plugin_inputs, subscribers,
                                     zmq_args, other_args)

        return plugin_config


class Plugin(ZMQInputClient):
    """
    This is the parent class for all plugins. All plugins must implement
    their own process method which is called when a message is received.
    """

    __metaclass__ = ABCMeta

    def __init__(self, inputs, outputs, zmq_args=None, **kwargs):
        """
        Constructor

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

        if zmq_args is None:
            zmq_args = {}

        for key, value in kwargs.items():
            setattr(self, key, value)

        super(Plugin, self).__init__(**zmq_args)

    def __repr__(self):
        return f"<Plugin name={self.name}>"

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

    @staticmethod
    def create_plugin(plugin_config):
        """
        Static utility method that instantiates extensions of the Plugin class

        Params:
            plugin_config: Plugin configuration associated with Plugin instance

        Returns:
            Plugin - New Plugin extension

        Raises:
            ValueError:   if any of the required config values are missing
                          or plugin class can not be imported/loaded
        """
        name = plugin_config.name
        module_name = name.rsplit(".", 1)[0]
        class_name = name.rsplit(".", 1)[-1]

        module = import_module(module_name)
        if module is None:
            log.error(f"Unable to locate plugin module '{module_name}'")
            return None

        plugin_class = getattr(module, class_name)
        if plugin_class is None:
            log.error(f"Unable to locate plugin class '{name}'")
            return None

        plugin_instance = plugin_class(
            inputs=plugin_config.inputs,
            outputs=plugin_config.outputs,
            zmq_args=plugin_config.zmq_args,
            **plugin_config.kwargs
        )

        if plugin_instance is None:
            log.error(f"Unable to create plugin instance for '{name}'")

        return plugin_instance
