from abc import ABCMeta, abstractmethod

import enum
import copy

from importlib import import_module

import gevent
import gevent.monkey

gevent.monkey.patch_all()

from ait.core import log, cfg
from .client import ZMQInputClient


class Type(enum.Enum):
    """
    Enumeration for Plugin type: standard plugin (greenlet) or process-based
    """
    STANDARD = enum.auto()
    PROCESS = enum.auto()

    @classmethod
    def value_of(cls, value, default):
        """
        Class method that returns a Type enum based on string value.
        If value is None or does not match, then Type.GREENLET is returned
        by default.

        Params:
            value: Name associated with the enum
            default: Default value to be returned, can be None

        Returns:  plugin.Type - Type enum instance
        """
        if value:
            for k, v in cls.__members__.items():
                if k.lower() == value.lower():
                    return v
        if default:
            return default
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{value}'")


class PluginConfig(object):
    """
    Data-struct for plugin information.
    Would be useful if we allow multiple plugins to run in a common
    child-process
    """

    def __init__(self, name, inputs=[], outputs=[], zmq_args=None, **kwargs):
        """
        Constructor

        Params:
            name:       Name of the Plugin class
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
        self.inputs = inputs
        self.outputs = outputs
        self.zmq_args = zmq_args
        self.kwargs = kwargs

    # TODO: do we really need these?
    def get_zmq_context(self):
        return self.zmq_args.get('context', None)

    def set_zmq_context(self, context):
        self.zmq_args['context'] = context

    @staticmethod
    def build_from_config(config, zmq_args=None):
        """
        Static method that extracts information from AIT Plugin
        configuration and returns a newly instantiated
        PluginConfig object.
        Required configuration that is missing will result in
        error.

        Params:
            config: AIT configuration for a plugin
            zmq_args: ZMQ settings

        Returns:  PluginConfig - New PluginConfig built from config

        Raises:
            ValueError:   if any of the required config values are missing
        """

        # Make a copy of the config that we can manipulate
        other_args = copy.deepcopy(config)

        # Extract name and ensure it is defined
        name = other_args.pop("name", None)
        if name is None:
            raise (cfg.AitConfigMissing("plugin name"))

        plugin_inputs = other_args.pop("inputs")
        if not plugin_inputs:
            log.warn(f"No plugin inputs specified for {name}")
            plugin_inputs = []

        subscribers = other_args.pop("outputs")
        if not subscribers:
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
        Static utility method that instantiates extensions
        of the Plugin class.

        Params:
            plugin_config: Plugin configuration associated with Plugin instance

        Returns:  Plugin - New Plugin extension

        """
        name = plugin_config.name
        module_name = name.rsplit(".", 1)[0]
        class_name = name.rsplit(".", 1)[-1]

        module = import_module(module_name)
        plugin_class = getattr(module, class_name)
        instance = plugin_class(
            plugin_config.inputs,
            plugin_config.outputs,
            plugin_config.zmq_args,
            plugin_config.other_args,
        )

        return instance
