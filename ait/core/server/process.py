import zmq.green as zmq

import copy
import sys
import gevent
import gipc  # type: ignore
import setproctitle  # type: ignore

from ait.core import log
from .plugin import Plugin
from .broker import Broker


class PluginsProcess(object):
    """
    PluginsProcess allows a set of plugins to be run in a
    separate process.  Since plugins are all greenlets,
    the process runs them within a cleaned-up gevent context
    (thanks to GIPC).

    An instance is first populated with a set of PluginConfig's instances.

    When the spawn_process() method is called, GIPC creates a new process.
    This process creates a fresh ZeroMQ Context, instantiates
    all managed Plugins (using the PluginConfigs), and then runs the
    Plugins within a gevent-space that is isolated from other processes.
    """

    def __init__(self, namespace):
        """
        Constructor

        Params:
            namespace:  Namespace for the child-process
        """
        if namespace is None:
            raise ValueError("No plugin process namespace provided")

        self._namespace = namespace
        self._process = None
        self._plugin_infos = []
        self._spawned = False

    def __repr__(self):
        """
        Returns string representation for this instance

        Returns:
            string - Instance string repr
        """
        return f"<PluginsProcess name={self._namespace}>"

    def get_plugin_names(self, use_short_names=True):
        """
        Returns a list of plugin names (short versions) managed by instance
        Returns: List of plugin names
        """
        return [pi.short_name if use_short_names else pi.name
                for pi in self._plugin_infos]

    def get_plugin_outputs(self, use_short_names=True):
        """
        Return dict of plugin name to list of outputs, where outputs
        will subscribe to the plugin.  The map keys represent either
        the plugin's fullname or shortname, depending on the
        value of use_short_names

        Args:
            use_short_names: boolean
                If true, plugin key will be short-name, otherwise full name

        Returns:
            Map of plugin names to list of outputs names which should subscribe to plugin

        """
        plugin_dict = {}
        for p_info in self._plugin_infos:
            output_list = []
            plugin_key = p_info.short_name if use_short_names else p_info.name
            for plugin_output in p_info.outputs:
                output_list.append(plugin_output)
            plugin_dict[plugin_key] = output_list
        return plugin_dict

    def add_plugin_info(self, plugin_info):
        """
        Adds a PluginConfig instance to be managed

        Params:
            plugin_info:  Instance of PluginConfig

        Raises:
            RuntimeError if the process is already running
        """
        if self._spawned:
            raise RuntimeError("Cannot add plugin info after process has "
                               "been spawned")

        if plugin_info is not None:
            self._plugin_infos.append(plugin_info)

    def spawn_process(self):
        """
        Spawns the child-process which will build and run the associated
        Plugins

        Raises:
            RuntimeError if this method is called more than once
        """
        if self._spawned:
            raise RuntimeError("Cannot spawn process more than once")

        self._spawned = True

        # assign the method to be invoked
        proc_target = PluginsProcess.start_plugins_process

        # create copy of the args to be passed to process
        proc_args = (self._namespace, copy.deepcopy(self._plugin_infos))

        # Call GIPC start_process
        log.info(f"Starting plugin-process '{self._namespace}'...")
        self._process = gipc.start_process(target=proc_target, args=proc_args)

    @staticmethod
    def start_plugins_process(namespace, plugin_info_list):
        """
        Creates and runs Plugins built from the plugin-info list.
        This method is expected to run within its own process.

        Params:
            namespace: Namespace for the child-process
            plugin_info_list: List of PluginConfig's
        """

        # Update the plugin process title
        PluginsProcess.update_process_name(namespace)

        # Load all plugins and return as list
        plugin_list = PluginsProcess.load_plugins(namespace, plugin_info_list)

        # Setup input subscriptions for the plugins
        PluginsProcess.subscribe_plugins_to_inputs(plugin_list)

        # Run all of the plugins and wait for them to complete (does not return)
        PluginsProcess.start_and_join_all(namespace, plugin_list)

    @staticmethod
    def load_plugins(namespace, plugin_info_list):

        # List of plugins to be returned
        plugin_list = []

        # Now that we are in own process, create a ZMQ Context that
        # will be shared amongst the managed greenlets
        proc_context = zmq.Context()

        # Instantiate each of the Plugins, add to list
        for p_info in plugin_info_list:
            plugin_name = p_info.name
            try:
                plugin = PluginsProcess.create_plugin(p_info, proc_context)
                if plugin is None:
                    log.info(f"Unable to create {plugin_name}, will not be "
                             f"added to {namespace} plugins list")
                else:
                    log.debug(f"Adding process-greenlet '{plugin_name}' to "
                              f"'{namespace}' plugins list")
                    plugin_list.append(plugin)

            except Exception:
                exc_type, exc_value, tb = sys.exc_info()
                log.error(f"{exc_type} creating plugin '{plugin_name}'' for "
                          f"process '{namespace}'': {exc_value}")

        return plugin_list

    @staticmethod
    def create_plugin(plugin_info, zmq_context):
        """
        Builds and initializes Plugin instance, passing the stored arguments
        for inputs, outputs, ZMQ args, and other keywords arguments

        Params:
            plugin_info: Instance of PluginConfig
            zmq_context: ZeroMQ context to be used by Plugin

        Returns:
            Plugin - New Plugin instance
        """

        # If provided with a context, then ensure the pluginconfig's
        # zeromq args section is updated to use it
        if zmq_context:
            plugin_info.set_zmq_context(zmq_context)

        # construct the plugin
        plugin = Plugin.create_plugin(plugin_info)

        return plugin

    @staticmethod
    def subscribe_plugins_to_inputs(plugin_list):
        """
        Subscribe all plugins to their associated inputs only.
        This is handled separately from outputs because the
        plugin which is performing the subscription to the input resides
        in this process.
        Output subscriptions must occur in the process where the stream
        resides, which is the server's process

        Args:
            plugin_list: List of Plugin's
        """
        for plugin in plugin_list:
            for input_ in plugin.inputs:
                Broker.subscribe(plugin, input_)

    @staticmethod
    def start_and_join_all(namespace, plugin_list):
        """
        Start all of the plugins in the list.
        Then wait for them to complete with a call to gevent.joinall()

        Args:
            namespace: Process namespace (used for logging)
            plugin_list: List of Plugin's to be started
        """

        # Start all of the plugin-gevents
        for greenlet in plugin_list:
            log.info(f"Starting {greenlet} greenlet in process "
                     f"'{namespace}'...")
            greenlet.start()

        # Wait for Plugins to finish
        gevent.joinall(plugin_list)

    @staticmethod
    def update_process_name(namespace):
        """
        Renames the process title associated with current process.
        Without this, process has the same title as original server.

        Args:
            namespace: AIT process namespace
        """
        plugin_proc_name = f"plugin-process.{namespace}"

        updated_title = f"ait-server-{plugin_proc_name}"
        orig_title = setproctitle.getproctitle()
        if orig_title is not None:
            updated_title = f"{orig_title} {plugin_proc_name}"

        setproctitle.setproctitle(updated_title)

    def abort(self):
        """
        Aborts the spawned child process associated with the Plugin

        Returns:    boolean - True if process was terminated, False otherwise
        """
        if self._process is not None:
            log.info(f"Terminating plugin-process '{self._namespace}'...")
            self._process.terminate()
            self._process = None
            return True

        return False
