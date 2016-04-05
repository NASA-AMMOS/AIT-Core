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

        If pathname is not given, it defaults to:

            ${BLISS_ROOT}/config/${BLISS_MISSION}/config.yaml
        """
        if pathname is None:
            pathname = os.path.join(BlissConfig.CONFIG_DIR, 'config.yaml')

        if pathname and config is None:
            config  = self._load(pathname)
        elif config is None:
            config = { }

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
