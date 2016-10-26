# Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Configuration

The bliss.config module provides classes and functions to manage
(re)configurable aspects of BLISS via a YAML configuration file.

"""

import os
import platform
import sys
import datetime
import re

import yaml

from bliss import log


DEFAULT_PATH_VARS = {
    'year' : datetime.datetime.utcnow().strftime('%Y'),
    'doy' : datetime.datetime.utcnow().strftime('%j')
}

def expandConfigPaths (config, prefix=None, pathvars=None, *keys):
    """Updates all relative configuration paths in dictionary config,
    which contain a key in keys, by prepending prefix.

    If keys is is omitted, it defaults to 'directory', 'file',
    'filename', 'path', 'pathname'.

    See expandPath().
    """
    if len(keys) == 0:
        keys = 'directory', 'file', 'filename', 'path', 'pathname'

    for name, value in config.items():
        if name in keys and type(name) is str:
            expanded = expandPath(value, prefix)
            cleaned = replaceVariables(expanded, pathvars)
            config[name] = cleaned[0] if len(cleaned) == 1 else cleaned
            # config[name] = expanded
        elif type(value) is dict:
            expandConfigPaths(value, prefix, pathvars, *keys)


def expandPath (pathname, prefix=None):
    """Return pathname as an absolute path, either expanded by the users
    home directory ("~") or with prefix prepended.
    """
    if prefix is None:
        prefix = ''

    expanded = pathname

    if pathname[0] == '~':
        expanded = os.path.expanduser(pathname)
    elif pathname[0] != '/':
        expanded = os.path.join(prefix, pathname)

    return os.path.abspath(expanded)

def replaceVariables(path, pathvars=None):
    """Return absolute path with path variables replaced as applicable"""

    # if path variables is None, let's use the default
    if pathvars is None:
        pathvars = DEFAULT_PATH_VARS

    paths = [ path ]

    # Replace all path variables with their specified values
    regex = re.compile('\$\{(.*?)\}')

    # Find all the variables in path using the regex
    for k in regex.findall(path):
        # Check if the key is in path variables map
        if k in pathvars:
            # get the str or list of values
            v = pathvars[k]

            # new path list for this variable
            newpaths = [ ]

            # Value of variable must be in (string, integer, list)
            if type(v) is dict:
                msg = "Path variable must refer to string, integer, or list"
                raise TypeError(msg)

            # start with a list
            valuelist = v if type(v) is list else [ v ]

            for p in paths:
                for v in valuelist:
                    newpaths.append(p.replace('${%s}' % k, str(v)))

            paths = newpaths

    return paths

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
    file and logs an error message via bliss.log.error().
    """
    config = None

    try:
        if filename:
            data = open(filename, 'rt')

        config = yaml.load(data)

        if type(data) is file:
            data.close()
    except IOError, e:
        msg = 'Could not read BLISS configuration file "%s": %s'
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


class BlissConfig (object):
    """BlissConfig

    A BlissConfig object holds configuration parameters read from a
    YAML configuration file.  The YAML data structure has three levels
    of parameters, in order: defaults, platform-specific, and
    host-specific, each taking precedence over the previous one.

    NOTE: The platform string is Python's sys.platform, i.e. 'linux2',
    'darwin', 'win32'.
    """
    _ROOT_DIR = os.path.abspath(os.environ.get('BLISS_ROOT', os.getcwd()))

    if 'BLISS_ROOT' not in os.environ:
        log.warn('BLISS_ROOT not set.  Defaulting to "%s"' % _ROOT_DIR)

    def __init__ (self, filename=None, data=None, config=None, pathvars=None):
        """Creates a new BlissConfig object with configuration data read from
        the given YAML configuration file or passed-in via the given
        config dictionary.

        If filename and data are not given, it defaults to the following in
        order depending on the presence of environment variables::

            ${BLISS_CONFIG}
            ${BLISS_ROOT}/config/config.yaml
            /current_work_directory/config/config.yaml

        """
        self._filename = None
        self._pathvars = None

        if data is None and filename is None:
            if 'BLISS_CONFIG' in os.environ:
                filename = os.path.abspath(os.environ.get('BLISS_CONFIG'))
            else:
                msg = 'BLISS_CONFIG not set. Falling back to BLISS_ROOT or CWD'
                log.warn(msg)
                filename = os.path.join(self._directory, 'config.yaml')

        if config is None:
            self.reload(filename, data)
        else:
            self._config   = config
            self._filename = filename

    def __contains__ (self, name):
        """Returns True if name is in this BlissConfig, False otherwise."""
        return name in self._config

    def __eq__ (self, other):
        return isinstance(other, BlissConfig) and self._config == other._config

    def __ne__ (self, other):
        return not self == other

    def __getattr__ (self, name):
        """Returns the attribute value BlissConfig.name."""
        if name not in self:
            raise AttributeError('No attribute "%s" in BlissConfig.' % name)
        return self._getattr_(name)

    def __getitem__ (self, name):
        """Returns the value of BlissConfig[name]."""
        if name not in self:
            raise KeyError('No key "%s" in BlissConfig.' % name)
        return self._getattr_(name)

    def __repr__ (self):
        """Return a printable representation of this BlissConfig."""
        args = [ ]

        if self._filename:
            args.append('filename="%s"' % self._filename)

        args.append('data=%s' % self._config)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(args))

    def __str__ (self):
        """Return a string representation of this BlissConfig."""
        return self.__repr__()

    def _getattr_ (self, name):
        """Internal method.  Used by __getattr__() and __getitem__()."""
        value = self._config.get(name)

        if type(value) is dict:
            value = BlissConfig(self._filename, config=value)

        return value

    @property
    def _directory (self):
        """The directory for this BlissConfig."""
        if self._filename is None:
            return os.path.join(self._ROOT_DIR, 'config')
        else:
            return os.path.dirname(self._filename)

    @property
    def _hostname (self):
        """The hostname for this BlissConfig."""
        return platform.node().split('.')[0]

    @property
    def _platform (self):
        """The platform for this BlissConfig."""
        return sys.platform

    @property
    def pathvars (self):
        """The path variables key-value map to be used to replace special
        keywords in the paths. Any variable in the config or default variable
        map can be used.
        """
        return self._pathvars

    @pathvars.setter
    def pathvars (self, value):
        """Set the path variables key-value map for manipulating the paths in
        this BlissConfig.
        """
        self._pathvars = value

    @property
    def _datapaths(self):
        """Returns a simple key-value map for easy access to data paths"""
        paths = { }
        data = self._config['data']
        for k in data:
            paths[k] = data[k]['path']

        return paths

    def reload (self, filename=None, data=None):
        """Reloads the a BLISS configuration.

        The BLISS configuration is automatically loaded when the BLISS
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
            if self.pathvars is None:
                self.pathvars = DEFAULT_PATH_VARS
                self.pathvars['platform'] = self._platform
                self.pathvars['hostname'] = self._hostname
                self.pathvars = merge(self.pathvars, self._config)
            else:
                self.addPathVariables(self._config)

            expandConfigPaths(self._config, self._directory, self.pathvars)
        else:
            self._config = { }

    def getDefaultFilename(self):
        if 'BLISS_CONFIG' in os.environ:
            filename = os.path.abspath(os.environ.get('BLISS_CONFIG'))
        else:
            msg = 'BLISS_CONFIG not set. Falling back to BLISS_ROOT or CWD'
            log.warn(msg)
            filename = os.path.join(self._directory, 'config.yaml')

        return filename

    def addPathVariables(self, pathvars):
        """ Adds path variables to the pathvars map property"""
        if type(pathvars) is dict:
            self.pathvars = merge(self.pathvars, pathvars)
