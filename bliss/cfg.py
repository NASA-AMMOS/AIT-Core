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

import yaml

import logging

log = logging.getLogger('bliss')

def expandConfigPaths (config, prefix=None, *keys):
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
            config[name] = expandPath(value, prefix)
        elif type(value) is dict:
            expandConfigPaths(value, prefix, *keys)


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
        log.warning('BLISS_ROOT not set.  Defaulting to "%s"' % _ROOT_DIR)


    def __init__ (self, filename=None, data=None, config=None):
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

        if data is None and filename is None:
            if 'BLISS_CONFIG' in os.environ:
                filename = os.path.abspath(os.environ.get('BLISS_CONFIG'))
            else:
                msg = 'BLISS_CONFIG not set. Falling back to BLISS_ROOT or CWD'
                log.warning(msg)
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
            expandConfigPaths(self._config, self._directory)
        else:
            self._config = { }
