"""
BLISS Configuration

The bliss.config module provides classes and functions to manage
(re)configurable aspects of BLISS via a YAML configuration file.

"""

"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import os
import platform
import sys
from pkg_resources import Requirement, resource_filename

import yaml

from bliss import log
from bliss import util


class BlissConfig (object):
    ROOT_DIR   = os.environ.get('BLISS_ROOT', '/')
    MISSION    = os.environ.get('BLISS_MISSION', 'ECOSTRESS')
    CONFIG_DIR = os.path.join(ROOT_DIR, 'config', MISSION.lower())


    """BlissConfig

    A BlissConfig object holds configuration parameters read from a
    YAML configuration file.  The YAML data structure has three levels
    of parameters, in order: defaults, platform-specific, and
    host-specific, each taking precedence over the previous one.  For
    example:

        default:
            ISS:
                apiport: 9090
                bticard: 0
                desc:    ISS PL/MDM Simulator
                path:    bin/oco3-isssim.py
                rtaddr:  15

        win32:
            ISS:
                bticard: 6

        eco-egse1:
            ISS:
                bticard: 1

    In this case:

        >>> config = bliss.BlissConfig()
        >>> config.ISS.bticard

    The value of bticard will be 1 on eco-egse1, 6 on Windows, and 0
    otherwise.

    NOTE: The platform string is Python's sys.platform, i.e. 'linux2',
    'darwin', 'win32'.

    """


    def __init__ (self, pathname=None, config=None):
        """Creates a new BlissConfig object with configuration data read from
        the given YAML configuration file or passed-in via the given
        config dictionary.

        If pathname is not given, it attempts to load the default configuration
        values as set in the BLISS settings.yaml file. If no valid config
        file can be located this way, it will default to an empty dictionary.

        If pathname is not give it will attempt to locate a 'config.yaml' file
        using the 'config_path' attribute in the default settings.yaml file
        located in the bliss package. If a configuration file cannot be located
        in this way then an empty configuration dictionary will be set.
        """
        if pathname is None:
            # Locate the BLISS package settings file.
            package_location = Requirement.parse("bliss-core")
            settings_file = resource_filename(
                package_location,
                os.path.join("bliss", "data", "settings.yaml")
            )

            # Try to pull out the 'config_path' settings value from the
            # default BLISS package settings file.
            with open(settings_file, 'r') as config_in:
                try: 
                    loaded_config = yaml.load(config_in)
                except IOError, e:
                    msg = 'Could not read BLISS settings.yaml file {} : {}'
                    log.error(msg, settings_file, str(e))

            try:
                config_path = loaded_config['config_path']
            except KeyError, e:
                config_path = None
                msg = 'Could not locate "config_path" setting {} : {}'
                log.error(msg, settings_file, str(e))
                
            # If we're given a relative path for the config path we assume
            # that it is stored within bliss-core package. The most likely
            # situation for this would be during development when the test
            # configuration values are used.
            if config_path:
                if not os.path.isabs(config_path):
                    pathname = os.path.join(
                        package_location.key,
                        config_path,
                        "config.yaml"
                    )
                else:
                    pathname = os.path.join(config_path, "config.yaml")

                if not os.path.isfile(pathname):
                    pathname = None

        if pathname and config is None:
            config  = self._load(pathname)

        if config is None:
            config = {}

        self._pathname = pathname
        self._config   = config
        self._hostname = platform.node().split('.')[0]
        self._platform = sys.platform


    def __getattr__ (self, name):
        """Returns this BlissConfig's attribute with the given name."""
        empty  = { }
        config = self._config or empty

        if name not in config:
            config = self._config.get(self._hostname, empty)

        if name not in config:
            config = self._config.get(self._platform, empty)

        if name not in config:
            config = self._config.get('default', empty)

        value = config.get(name, None)

        if type(value) is dict:
            value = BlissConfig(self._pathname, value)

        return value


    def __getitem__ (self, name):
        """Returns this BlissConfig's attribute with the given name."""
        return self._config[name]


    def __repr__ (self):
        return self._config.__repr__()


    def __str__ (self):
        return self._config.__str__()


    def _load (self, pathname):
        """Loads the given YAML configuration file.

        If there was an error reading from the configuration file, it is
        logged via bliss.log.error and None is returned.
        """
        config = None

        try:
            with open(pathname, 'rt') as stream:
                config = yaml.load(stream)
        except IOError, e:
            msg = 'Could not read BLISS configuration file "%s": %s'
            log.error(msg, pathname, str(e))

        if config:
            config = self._updatePaths( self._updateDefaults(config) )

        return config


    def _updateDefaults (self, config):
        """Updates all configuration defaults in given config dictionary.

        For example, given the following YAML configuration (the
        mapping to a Python dictionary is straightforward):

        default:
          ISS:
            apiport: 9090
            bticard: 0
            desc:    ISS PL/MDM Simulator
            path:    bin/oco3-isssim.py
            rtaddr:  15

          win32:
            ISS:
            bticard: 6

        The returned dictionary will include an updated win32 ISS
        simulator entry:

          ISS:
            apiport: 9090
            bticard: 6
            desc:    ISS PL/MDM Simulator
            path:    bin/oco3-isssim.py
            rtaddr:  15
        """
        empty   = { }
        default = config.get('default', empty)
        groups  = (name for name in config.keys() if name != 'default')

        for group in groups:
            for subgroup, subconfig in config[group].items():
                subdefaults = default.get(subgroup  , empty)
                util.setDictDefaults(subconfig, subdefaults)

        return config


    def _updatePaths (self, config):
        """Updates all relative configuration paths in given config dictionary
        by prepending the value of ${BLISS_ROOT}/config/${BLISS_MISSION}.
        """
        update = ('directory', 'file', 'filename', 'path', 'pathname')

        for key, val in config.items():
            if key in update:
                if type(val) is str:
                    if val[0] == '/':
                        fullpath = val
                    elif val[0] == '~':
                        fullpath = os.path.expanduser(val)
                    else:
                        joined   = os.path.join(BlissConfig.CONFIG_DIR, val)
                        fullpath = os.path.abspath(joined)
                    config[key] = fullpath
            elif type(val) is dict:
                config[key] = self._updatePaths(val)

        return config


    def dict (self):
        """Return the underlying dictionary for this BlissConfig."""
        return self._config


    @property
    def hostname (self):
        """The hostname for this BlissConfig."""
        return self._hostname


    @property
    def platform (self):
        """The platform for this BlissConfig."""
        return self._platform
