# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2013, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
AIT Configuration

The ait.core.cfg module provides classes and functions to manage
(re)configurable aspects of AIT via a YAML configuration file.

"""

import os
import platform
import sys
import time
import re

import yaml

import ait
from ait.core import log, util


DEFAULT_PATH_VARS = {
    'year': time.strftime('%Y', time.gmtime()),
    'doy' : time.strftime('%j', time.gmtime())
}

PATH_KEYS = 'directory', 'file', 'filename', 'path', 'pathname'

def expandConfigPaths (config, prefix=None, datetime=None, pathvars=None, parameter_key='', *keys):
    """Updates all relative configuration paths in dictionary config,
    which contain a key in keys, by prepending prefix.

    If keys is omitted, it defaults to 'directory', 'file',
    'filename', 'path', 'pathname'.

    See util.expandPath().
    """
    if len(keys) == 0:
        keys = PATH_KEYS

    for name, value in config.items():
        if name in keys and type(name) is str:
            expanded = util.expandPath(value, prefix)
            cleaned = replaceVariables(expanded, datetime=datetime, pathvars=pathvars)

            for p in cleaned:
                if not os.path.exists(p):
                    msg = "Config parameter {}.{} specifies nonexistent path {}".format(parameter_key, name, p)
                    log.warn(msg)

            config[name] = cleaned[0] if len(cleaned) == 1 else cleaned

        elif type(value) is dict:
            param_key = name if parameter_key == '' else parameter_key + '.' + name
            expandConfigPaths(value, prefix, datetime, pathvars, param_key, *keys)


def replaceVariables(path, datetime=None, pathvars=None):
    """Return absolute path with path variables replaced as applicable"""

    if datetime is None:
        datetime = time.gmtime()

    # if path variables are not given, set as empty list
    if pathvars is None:
        pathvars = [ ]

    # create an init path list to loop through
    if isinstance(path, list):
        path_list = path
    else:
        path_list = [ path ]

    # Set up the regex to search for variables
    regex = re.compile('\$\{(.*?)\}')

    # create a newpath list that will hold the 'cleaned' paths
    # with variables and strftime format directives replaced
    newpath_list = [ ]

    for p in path_list:
        # create temppath_list to be used a we work through the
        newpath_list.append(p)

        # Variable replacement
        # Find all the variables in path using the regex
        for k in regex.findall(p):
            # Check if the key is in path variables map
            if k in pathvars:
                # get the str or list of values
                v = pathvars[k]

                # Check value of variable must be in (string, integer, list)
                if type(v) is dict:
                    msg = "Path variable must refer to string, integer, or list"
                    raise TypeError(msg)

                # get the list of possible variable values
                value_list = v if type(v) is list else [ v ]


                # create temp_list for now
                temp_list = []

                # loop through the most recent newpath list
                # need to do this every time in order to account for all possible
                # combinations
                # replace the variables
                # loop through the list of values and replace the variables
                for v in value_list:
                    for newpath in newpath_list:
                        # remove the path from newpath_list
                        temp_list.append(newpath.replace('${%s}' % k, str(v)))

                # replace newpath_list
                newpath_list = temp_list

        # strftime translation
        # Loop through newpath_list to do strftime translation
        for index, newpath in enumerate(newpath_list):
            # Apply strftime translation
            newpath_list[index] = time.strftime(newpath, datetime)

    return newpath_list


def flatten (d, *keys):
    """Flattens the dictionary d by merging keys in order such that later
    keys take precedence over earlier keys.

    """
    flat = { }

    for k in keys:
        flat = merge(flat, d.pop(k, { }))

    return flat


def loadYAML (filename=None, data=None):
    """Loads either the given YAML configuration file or YAML data.

    Returns None if there was an error reading from the configuration
    file and logs an error message via ait.core.log.error().
    """
    config = None

    try:
        if filename:
            data = open(filename, 'rt')

        config = yaml.load(data)

        if type(data) is file:
            data.close()
    except IOError, e:
        msg = 'Could not read AIT configuration file "%s": %s'
        log.error(msg, filename, str(e))

    return config


def merge (d, o):
    """Recursively merges keys from o into d and returns d."""
    for k in o.keys():
        if type(o[k]) is dict and k in d:
            merge(d[k], o[k])
        else:
            d[k] = o[k]
    return d



class AitConfigError(Exception):
    """Raised when a AIT configuration parameter is present, but
    is in some way incorrect."""
    pass



class AitConfigMissing(Exception):
    """Raised when a AIT configuration parameter is missing."""

    def __init__(self, param):
        values = param, ait.config._filename
        format = 'The parameter %s is missing from config.yaml (%s).'
        super(AitConfigMissing, self).__init__(format % values)
        self.param = param



class AitConfig (object):
    """AitConfig

    A AitConfig object holds configuration parameters read from a
    YAML configuration file.  The YAML data structure has three levels
    of parameters, in order: defaults, platform-specific, and
    host-specific, each taking precedence over the previous one.

    NOTE: The platform string is Python's sys.platform, i.e. 'linux2',
    'darwin', 'win32'.
    """
    _ROOT_DIR = os.path.abspath(os.environ.get('AIT_ROOT', os.getcwd()))

    if 'AIT_ROOT' not in os.environ:
        log.warn('AIT_ROOT not set.  Defaulting to "%s"' % _ROOT_DIR)

    def __init__ (self, filename=None, data=None, config=None, pathvars=None):
        """Creates a new AitConfig object with configuration data read from
        the given YAML configuration file or passed-in via the given
        config dictionary.

        If filename and data are not given, it defaults to the following in
        order depending on the presence of environment variables::

            ${AIT_CONFIG}

        """
        self._filename = None
        self._data = data
        self._datetime = time.gmtime()
        self._pathvars = pathvars

        if data is None and filename is None:
            if 'AIT_CONFIG' in os.environ:
                filename = os.path.abspath(os.environ.get('AIT_CONFIG'))
            else:
                msg = 'AIT_CONFIG is not set. Exiting ...'
                log.error(msg)
                raise ValueError(msg)

        if config is None:
            self.reload(filename, data)
        else:
            self._config   = config
            self._filename = filename

    def __contains__ (self, name):
        """Returns True if name is in this AitConfig, False otherwise."""
        return name in self._config

    def __eq__ (self, other):
        return isinstance(other, AitConfig) and self._config == other._config

    def __ne__ (self, other):
        return not self == other

    def __getattr__ (self, name):
        """Returns the attribute value AitConfig.name."""
        if name not in self:
            raise AttributeError('No attribute "%s" in AitConfig.' % name)
        return self._getattr_(name)

    def __getitem__ (self, name):
        """Returns the value of AitConfig[name]."""
        if name not in self:
            raise KeyError('No key "%s" in AitConfig.' % name)
        return self._getattr_(name)

    def __repr__ (self):
        """Return a printable representation of this AitConfig."""
        args = [ ]

        if self._filename:
            args.append('filename="%s"' % self._filename)

        args.append('data=%s' % self._config)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(args))

    def __str__ (self):
        """Return a string representation of this AitConfig."""
        return self.__repr__()

    def _getattr_ (self, name):
        """Internal method.  Used by __getattr__() and __getitem__()."""
        value = self._config.get(name)

        if type(value) is dict:
            value = AitConfig(self._filename, config=value)

        return value

    @property
    def _directory (self):
        """The directory for this AitConfig."""
        if self._filename is None:
            return os.path.join(self._ROOT_DIR, 'config')
        else:
            return os.path.dirname(self._filename)

    @property
    def _hostname (self):
        """The hostname for this AitConfig."""
        return platform.node().split('.')[0]

    @property
    def _platform (self):
        """The platform for this AitConfig."""
        return sys.platform

    @property
    def _datapaths(self):
        """Returns a simple key-value map for easy access to data paths"""
        paths = { }
        try:
            data = self._config['data']
            for k in data:
                paths[k] = data[k]['path']
        except KeyError as e:
            raise AitConfigMissing(e.message)
        except Exception as e:
            raise AitConfigError('Error reading data paths: %s' % e)

        return paths

    def reload (self, filename=None, data=None):
        """Reloads the a AIT configuration.

        The AIT configuration is automatically loaded when the AIT
        package is first imported.  To replace the configuration, call
        reload() (defaults to the current config.filename) or
        reload(new_filename).
        """
        if data is None and filename is None:
            filename = self._filename

        self._config   = loadYAML(filename, data)
        self._filename = filename

        if self._config is not None:
            keys         = 'default', self._platform, self._hostname
            self._config = flatten(self._config, *keys)

            # on reload, if pathvars have not been set, we want to start
            # with the defaults, add the platform and hostname, and
            # merge in all of the information provided in the config
            if self._pathvars is None:
                self._pathvars = self.getDefaultPathVariables()

            expandConfigPaths(self._config, 
                            self._directory,
                            self._datetime,
                            merge(self._config, self._pathvars))

        else:
            self._config = { }


    def get (self, name, default=None):
        """Returns the attribute value *AitConfig.name* or *default*
        if name does not exist.

        The name may be a series of attributes separated periods.  For
        example, "foo.bar.baz".  In that case, lookups are attempted
        in the following order until one succeeeds:

            1.  AitConfig['foo.bar.baz'], and
            2.  AitConfig.foo.bar.baz
            3.  (If both fail, return *default*)
        """
        if name in self:
            return self[name]

        config = self
        parts  = name.split('.')
        heads  = parts[:-1]
        tail   = parts[-1]

        for part in heads:
            if part in config and type(config[part]) is AitConfig:
                config = config[part]
            else:
                return default

        return config[tail] if tail in config else default


    def getDefaultFilename(self):
        if 'AIT_CONFIG' in os.environ:
            filename = os.path.abspath(os.environ.get('AIT_CONFIG'))
        else:
            msg = 'AIT_CONFIG not set. Falling back to AIT_ROOT or CWD'
            log.warn(msg)
            filename = os.path.join(self._directory, 'config.yaml')

        return filename

    def getDefaultPathVariables(self):
        pathvars = DEFAULT_PATH_VARS
        pathvars['platform'] = self._platform
        pathvars['hostname'] = self._hostname
        return pathvars

    def addPathVariables(self, pathvars):
        """ Adds path variables to the pathvars map property"""
        if type(pathvars) is dict:
            self._pathvars = merge(self._pathvars, pathvars)


# Create a singleton AitConfig accessible via ait.config
sys.modules['ait'].config = AitConfig()

# Re-initialize logging now that ait.config.logging.* parameters may exist.
log.reinit()
