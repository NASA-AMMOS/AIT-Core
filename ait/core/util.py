#!/usr/bin/env python2.7

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
AIT Utilities

The ait.core.util module provides general utility functions.
"""

import os
import pydoc
import stat
import sys
import time
import zlib
import types

import cPickle

import ait
from ait.core import log


class ObjectCache (object):
    def __init__(self, filename, loader):
      """Creates a new ObjectCache

      Caches the Python object returned by loader(filename), using
      Python's pickle object serialization mechanism.  An ObjectCache
      is useful when loader(filename) is slow.

      The result of loader(filename) is cached to cachename, the
      basename of filename with a '.pkl' extension.

      Use the load() method to load, either via loader(filename) or
      the pickled cache file, whichever was modified most recently.
      """
      self._loader    = loader
      self._dict      = None
      self._filename  = filename
      self._cachename = os.path.splitext(filename)[0] + '.pkl'


    @property
    def cachename(self):
      """The pickled cache filename"""
      return self._cachename


    @property
    def dirty(self):
      """True if the cache needs to be updated, False otherwise"""
      return not os.path.exists(self.cachename) or \
            (os.path.getmtime(self.filename) >
             os.path.getmtime(self.cachename))


    @property
    def filename(self):
      """The filename to cache via loader(filename)"""
      return self._filename


    def cache(self):
      """Caches the result of loader(filename) to cachename."""
      msg = 'Saving updates from more recent "%s" to "%s"'
      log.info(msg, self.filename, self.cachename)
      with open(self.cachename, 'wb') as output:
          cPickle.dump(self._dict, output, -1)


    def load(self):
        """Loads the Python object

        Loads the Python object, either via loader(filename) or the
        pickled cache file, whichever was modified most recently.
        """
        if self._dict is None:
            if self.dirty:
                self._dict = self._loader(self.filename)
                self.cache()
            else:
                with open(self.cachename, 'rb') as stream:
                    self._dict = cPickle.load(stream)

        return self._dict


if sys.platform == 'win32':
    # On Windows, the best timer is time.clock
    timer = time.clock
else:
    # On most other platforms the best timer is time.time
    timer = time.time



def __init_extensions__(modname, modsyms):
    """Initializes a module (given its name and :func:`globals()` symbol
    table) for AIT extensions.

    For every Python class defined in the given module, a
    `createXXX()`` function is added to the module (where XXX is the
    classname).  By default, the function calls the ``XXX()``
    constructor and returns a new instance of that class.  However, if
    AIT extensions are defined in ``config.yaml`` those extension
    classes are instantiated instead.  For example, with the following
    ``config.yaml``:

        .. code-block:: python
           extensions:
               ait.core.cmd.Cmd: FooCmd

    Anywhere AIT would create a :class:`Cmd` object (via
    :func:`createCmd()`) it will now create a ``FooCmd`` object
    instead.  Note: ``FooCmd`` should adhere to the same interface as
    :class:`ait.core.cmd.Cmd` (and probably inherit from it).
    """

    def createFunc (cls, extname):
        """Creates and returns a new ``createXXX()`` function to instantiate
        either the given class by class object (*cls*) or extension
        class name (*extname*).

        In the case of an extension class name, the first time the
        returned ``createXXX()`` is called, it attempts to lookup and
        load the class.  Thereafter, the loaded class is cached for
        subsequent calls.
        """
        def create(*args, **kwargs):
            if create.cls is None:
                parts = extname.rsplit('.', 1)
                if len(parts) > 1:
                    modname, clsname = parts
                    module           = pydoc.locate(modname)
                    if module is None:
                        raise ImportError('No module named %d' % modname)
                    create.cls = getattr(module, clsname)
                if create.cls is None:
                    raise ImportError('No class named %s' % extname)
            return create.cls(*args, **kwargs)
        create.cls = cls
        return create

    extensions = ait.config.get('extensions', None)

    for clsname, cls in modsyms.items():
        if not isinstance(cls, type):
            continue

        extname = None

        if extensions:
            extname = extensions.get(modname + '.' + clsname, None)

            if extname:
                cls    = None
                values = modname, clsname, extname
                log.info('Replacing %s.%s with custom extension: %s' % values)

        modsyms['create' + clsname] = createFunc(cls, extname)


def __load_functions__ (symtbl):
    """Loads all Python functions from the module specified in the
    ``functions`` configuration parameter (in config.yaml) into the given
    symbol table (Python dictionary).
    """
    modname = ait.config.get('functions', None)

    if modname:
        module = pydoc.locate(modname)

        if module is None:
            msg = 'No module named %d (from config.yaml functions: parameter)'
            raise ImportError(msg % modname)

        for name in dir(module):
            func = getattr(module, name)
            if callable(func):
                symtbl[name] = func


def crc32File(filename, skip=0):
    """Computes the CRC-32 of the contents of filename, optionally
    skipping a certain number of bytes at the beginning of the file.
    """
    with open(filename, 'rb') as stream:
        discard = stream.read(skip)
        return zlib.crc32(stream.read()) & 0xffffffff

def endianSwapU16(bytes):
    """Swaps pairs of bytes (16-bit words) in the given bytearray."""
    for b in range(0, len(bytes), 2):
        bytes[b], bytes[b + 1] = bytes[b + 1], bytes[b]
    return bytes


def setDictDefaults (d, defaults):
  """Sets all defaults for the given dictionary to those contained in a
  second defaults dictionary.  This convenience method calls:

    d.setdefault(key, value)

  for each key and value in the given defaults dictionary.
  """
  for key, val in defaults.items():
    d.setdefault(key, val)

  return d


def getDefaultDict(modname, config_key, loader, reload=False, filename=None):
    """Returns default AIT dictonary for modname

    This helper function encapulates the core logic necessary to
    (re)load, cache (via util.ObjectCache), and return the default
    dictionary.  For example, in ait.core.cmd:

    def getDefaultDict(reload=False):
        return ait.util.getDefaultDict(__name__, 'cmddict', CmdDict, reload)
    """
    module   = sys.modules[modname]
    default  = getattr(module, 'DefaultDict', None)

    if filename is None:
        filename = ait.config.get('%s.filename' % config_key, None)

    if filename is not None and (default is None or reload is True):
        try:
            default = ObjectCache(filename, loader).load()
            setattr(module, 'DefaultDict', default)
        except IOError, e:
            msg = 'Could not load default %s "%s": %s'
            log.error(msg, config_key, filename, str(e))

    return default or loader()


def getFileSize(filename):
    """Returns the size of filename in bytes."""
    return os.stat(filename)[stat.ST_SIZE]


def toBCD (n):

    """Converts the number n into Binary Coded Decimal."""
    bcd  = 0
    bits = 0

    while True:
        n, r  = divmod(n, 10)
        bcd  |= (r << bits)
        if n is 0:
            break
        bits += 4

    return bcd


def toFloat (str, default=None):
    """toFloat(str[, default]) -> float | default

    Converts the given string to a floating-point value.  If the
    string could not be converted, default (None) is returned.

    NOTE: This method is *significantly* more effecient than
    toNumber() as it only attempts to parse floating-point numbers,
    not integers or hexadecimal numbers.

    Examples:

    >>> f = toFloat("4.2")
    >>> assert type(f) is float and f == 4.2

    >>> f = toFloat("UNDEFINED", 999.9)
    >>> assert type(f) is float and f == 999.9

    >>> f = toFloat("Foo")
    >>> assert f is None
    """
    value = default

    try:
        value = float(str)
    except ValueError:
        pass

    return value


def toNumber (str, default=None):
    """toNumber(str[, default]) -> integer | float | default

    Converts the given string to a numeric value.  The string may be a
    hexadecimal, integer, or floating number.  If string could not be
    converted, default (None) is returned.

    Examples:

    >>> n = toNumber("0x2A")
    >>> assert type(n) is int and n == 42

    >>> n = toNumber("42")
    >>> assert type(n) is int and n == 42

    >>> n = toNumber("42.0")
    >>> assert type(n) is float and n == 42.0

    >>> n = toNumber("Foo", 42)
    >>> assert type(n) is int and n == 42

    >>> n = toNumber("Foo")
    >>> assert n is None
    """
    value = default

    try:
        if str.startswith("0x"):
            value = int(str, 16)
        else:
            try:
                value = int(str)
            except ValueError:
                value = float(str)
    except ValueError:
        pass

    return value

def toNumberOrStr (str):
    """toNumberOrStr(str) -> integer | float | string

    Converts the given string to a numeric value, if possible. Otherwise
    returns the input string
    """
    return toNumber(str, str)

def toRepr (obj):
    """toRepr(obj) -> string

    Converts the Python object to a string representation of the kind
    often returned by a class __repr__() method.
    """
    args  = [ ]
    names = [ ]

    if hasattr(obj, "__dict__"):
        names += getattr(obj, "__dict__").keys()
    if hasattr(obj, "__slots__"):
        names += getattr(obj, "__slots__")

    for name in names:
        value = getattr(obj, name)
        if value is not None:
            if type(value) is str:
                if len(value) > 32:
                    value = value[0:32] + "..."
                value = "'" + value + "'"
        args.append("%s=%s" % (name, str(value)))

    return "%s(%s)" % (obj.__class__.__name__, ", ".join(args))


def toStringDuration (duration):
    """Returns a description of the given duration in the most appropriate
    units (e.g. seconds, ms, us, or ns).
    """

    table = (
        ('%dms'      , 1e-3, 1e3),
        (u'%d\u03BCs', 1e-6, 1e6),
        ('%dns'      , 1e-9, 1e9)
    )

    if duration > 1:
        return '%fs' % duration

    for format, threshold, factor in table:
        if duration > threshold:
            return format % int(duration * factor)

    return '%fs' % duration

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

def listAllFiles (directory, suffix=None, abspath=False):
    """Returns the list of all files within the input directory and
    all subdirectories.
    """
    files = []

    directory = expandPath(directory)

    for dirpath, dirnames, filenames in os.walk(directory, followlinks=True):
        if suffix:
            filenames = [f for f in filenames if f.endswith(suffix)]

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if not abspath:
                filepath = os.path.relpath(filepath, start=directory)

                # os.path.join(path, filename)

            files.append(filepath)

    return files


class YAMLValidationError(Exception):
    def __init__(self, arg):
        # Set some exception infomation
        self.message = arg

        log.error(self.message)


class YAMLError(Exception):
    def __init__(self, arg):
        # Set some exception infomation
        self.message = arg

        log.error(self.message)


if __name__ == "__main__":
    # HACK: The 'doctest' module imports 'pdb' which imports 'cmd'.
    # Since none of these modules are using Python absolute imports, The
    # Python 'cmd' module conflicts with 'ait.cmd' (in this directory).
    # As a workaround, temporarily remove the current directory from our
    # path prior to importing doctest.

    import sys
    saved = sys.path.pop(0)
    import doctest
    sys.path.insert(0, saved)

    (num_failed, num_tests) = doctest.testmod()
    filename                = os.path.basename(__file__)

    if num_failed == 0:
        print "%-20s All %3d tests passed!" % (filename, num_tests)
