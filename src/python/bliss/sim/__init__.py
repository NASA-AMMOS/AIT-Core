"""
BLISS ISS Sim

The bliss.sim module provides the functionality for the sims to be
loaded using a YAML configuration file. It also provides a way to
proxy the simulations so that their endpoints can be reached.

"""

"""
Authors: Ben Bornstein

Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""

import sys
import os

import platform
import signal
import subprocess
import urlparse

import gevent
import requests
import yaml

import bliss


class SimConfig (object):
    """SimConfig

    A SimConfig object holds EGSE Simulator configuration parameters
    read from a YAML configuration file.  The YAML data structure has
    three levels of parameters, in order: defaults, platform-specific,
    and host-specific, each taking precedence over the previous one.
    For example:

        default:
            ISS:
                apiport: 9090
                bticard: 0
                desc:    ISS PL/MDM Simulator
                path:    bin/bliss-isssim.py
                rtaddr:  15

        win32:
            ISS:
                bticard: 6

        oco3-sim1:
            ISS:
                bticard: 1

    In this case:

        >>> config = bliss.sim.SimConfig()
        >>> config.ISS.bticard

    The value of bticard will be 1 on oco3-sim1, 6 on Windows, and 0
    otherwise.

    NOTE: The platform string is Python's sys.platform, i.e. 'linux2',
    'darwin', 'win32'.
    """


    def __init__ (self, pathname=None, config=None):
        """Creates a new SimConfig object with configuration data read from
        the given YAML configuration file or passed-in via the given
        config dictionary.

        If pathname is not given, it defaults to:

            ${BLISS_ROOT}/config/sim.yaml
        """
        if pathname is None:
            pathname = os.path.join(os.getenv('BLISS_ROOT'), 'config/sim.yaml')

        if pathname and config is None:
            config  = self._load(pathname)
        elif config is None:
            config = { }

        self._pathname = pathname
        self._config   = config
        self._hostname = platform.node().split('.')[0]
        self._platform = sys.platform


    def __getattr__ (self, name):
        """Returns this SimConfig's attribute with the given name."""
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
            value = SimConfig(self._pathname, value)

        return value

    def __getitem__ (self, name):
        """Returns this SimConfig's attribute with the given name."""
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
            msg = 'Could not read simulator configuration file "%s": %s'
            bliss.log.error(msg, pathname, str(e))

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
            path:    bin/bliss-isssim.py
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
            path:    bin/bliss-isssim.py
            rtaddr:  15
        """
        empty   = { }
        default = config.get('default', empty)
        groups  = (name for name in config.keys() if name != 'default')

        for group in groups:
            for subgroup, subconfig in config[group].items():
                subdefaults = default.get(subgroup  , empty)
                bliss.util.setDictDefaults(subconfig, subdefaults)

        return config


    def _updatePaths (self, config):
        """Updates all relative configuration paths in given config dictionary
        by prepending the value of ${BLISS_ROOT}.
        """
        update = ('file', 'filename', 'path', 'pathname')
        root   = os.getenv('BLISS_ROOT')

        for key, val in config.items():
            if key in update and type(val) is str and val[0] != '/':
                config[key] = os.path.abspath( os.path.join(root, val) )
            elif type(val) is dict:
                config[key] = self._updatePaths(val)

        return config


    def command (self, **kwargs):
        """Returns the command-line required to start the simulator
        represented by this SimConfig (sub-object) as an array,
        suitable for passing to Python's subprocess.Popen() or
        string.join()ing.

        For example:

            >>> config = bliss.sim.SimConfig()
            >>> config.command()
            [ ]

            >>> config.ISS.command()
            ['.../bin/python', '.../bin/bliss-isssim.py', '--rtaddr=15', ... ]

        Any command-line parameters / configuration arguments can be
        overridden by passing named parameters to this method, e.g.:

          >>> config.ISS.command(rtaddr=13)
          ['.../bin/python', '.../bin/bliss-isssim.py', '--rtaddr=13', ... ]
        """
        omit = ('desc', 'path')
        cmd  = [ ]

        if self.path:
          cmd.append(sys.executable)
          cmd.append(self.path)

          for name, value in self._config.items():
              if name in omit:
                  continue

              if name in kwargs:
                  value = kwargs[name]

              cmd.append('--%s=%s' % (name, value))

        return cmd


    def dict (self):
        return self._config


    @property
    def hostname (self):
        """The hostname for this SimConfig."""
        return self._hostname


    @property
    def platform (self):
        """The platform for this SimConfig."""
        return self._platform



Config = SimConfig()



class SimProxy (object):
    """SimProxy

    This class proxies an EGSE Simulator both for process control
    (e.g. start and stop) and REST API calls.  A SimProxy relies
    on a SimConfig for information about the simulator.
    """

    def __init__ (self, name):
        """Create a new SimProxy for the given EGSE simulator name.

        NOTE: A ValueError is raised if name does not exist in
        bliss.sim.Config.
        """
        self._name   = name
        self._config = getattr(Config, name)
        self._proc   = None

        if self._config is None:
            raise ValueError('Unrecognized simulator "%s"' % name)


    def _proxy (self, action, method='GET', **kwargs):
        """Proxies the given action via the EGSE simulator's REST API."""
        retries  = kwargs.pop('_retries', 0    )
        sleep    = kwargs.pop('_sleep'  , 1    )
        response = None
        url      = urlparse.urljoin(self.url, action)

        for n in range(retries + 1):
            if n > 0:
                gevent.sleep(sleep)

            try:
                response = requests.request(method, url, params=kwargs)
                break
            except requests.ConnectionError, e:
                pass
            except requests.HTTPError, e:
                bliss.log.error('%s failed: %s' % (url, str(e)))

        return response


    @property
    def active (self):
        """Indicates whether or not this EGSE simulator is running."""
        active = False

        try:
            active = self._proc is not None and self._proc.poll() is None

            if not active:
                active = self.status(retries=0) == requests.codes.ok
        except OSError, e:
            pass

        return active


    @property
    def name (self):
        """The EGSE simulator name."""
        return self._name


    @property
    def process (self):
        """The underlying EGSE simulator process."""
        return self._proc


    @property
    def url (self):
        """The EGSE simulator REST API URL."""
        # Use IPv4 127.0.0.1 loopback address instead of localhost.
        # Depending on the OS, the latter will attempt a connection on
        # multiple interfaces (e.g. IPv4, IPv6).  For example:
        #
        #     $ wget http://localhost:1234
        #     Resolving localhost... ::1, fe80::1, 127.0.0.1
        #     Connecting to localhost|::1|:1234... failed: Connection refused.
        #     Connecting to localhost|fe80::1|:1234...
        #
        #     $ wget http://127.0.0.1:1234
        #     Connecting to 127.0.0.1:1234... failed: Connection refused.
        host = '127.0.0.1'
        return 'http://%s:%d' % (host, self._config.apiport)


    def execute (self, action, method='GET', **kwargs):
        """Executes the EGSE simulator action with optional arguments."""
        func = getattr(self, action, None)

        if func is None:
            return self._proxy(action, method, **kwargs)
        else:
            return func(**kwargs)


    def start (self, **kwargs):
        """Starts the proxied EGSE simulator.

        Command-line arguments are determined from the appropriate
        SimConfig, but may be overridden by passing named parameters
        to this method.
        """
        if self.active:
            bliss.log.info('%s EGSE simulator already running.' % self._name)
            status = requests.codes.ok
        else:
            cmd = self._config.command(**kwargs)
            msg = 'Running EGSE simulator %s via %s'
            bliss.log.info(msg, self._name, ' '.join(cmd))
            self._proc = subprocess.Popen(cmd)
            status     = self.status()

        return status


    def stop (self, **kwargs):
        """Stops the proxied EGSE simulator."""
        status = requests.codes.ok

        if not self.active:
            bliss.log.info('%s EGSE simulator already stopped.' % self._name)
        else:
            bliss.log.info("Stopping %s EGSE simulator." % self._name)
            url = urlparse.urljoin(self.url, 'stop')

            try:
                response = requests.post(url)
                status   = response.status_code
            except requests.ConnectionError as e:
                pass

            gevent.sleep(0.25)
            if self.active:
                msg  = 'Failed graceful shutdown %s EGSE simulator.'
                bliss.log.error(msg, self._name)
                bliss.log.info('Attempting to force kill process')
                try:
                    os.kill(self._proc.pid, signal.SIGINT)
                except Exception as e:
                    pass
                finally:
                    if self.active:
                        self._proc.kill()

            gevent.sleep(0.25)
            if self.active:
                status = requests.codes.bad

        return status


    def status (self, retries=2):
        """Returns this simulator's status by making an REST API call."""
        response = self._proxy('status', method='GET', _retries=retries)
        status   = requests.codes.not_found

        if response:
            status = response.status_code

        return status


def getSim (name):
    """Returns the EGSE simulator with the given name.

    If you already know the name of the EGSE simulator (i.e. its not
    passed-in via user input) you can access the simulator directly by
    name, e.g. bliss.sim.ISS.
    """
    sim = globals().get(name, None)

    if not isinstance(sim, SimProxy):
        sim = None

    return sim


def getSims ():
    """Returns a list of all EGSE simulators."""
    return [ sim for sim in globals().values() if isinstance(sim, SimProxy) ]


ISS  = SimProxy('ISS')
