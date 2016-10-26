#!/usr/bin/env python
#
# Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Utilities

The bliss.util module provides general utility functions.
"""

import os
import stat
import sys
import time
import zlib
import types

import cPickle

import bliss


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
      bliss.log.info(msg, self.filename, self.cachename)
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


def getDefaultDict(module_name, config_key, loader, reload=False, filename=None):
    """Returns default BLISS dictonary for module_name

    This helper function encapulates the core logic necessary to
    (re)load, cache (via bliss.util.ObjectCache), and return the
    default dictionary.  For example, in bliss.cmd:

    def getDefaultDict(reload=False):
      return bliss.util.getDefaultDict(__name__, 'cmddict', CmdDict, reload)
    """
    module   = sys.modules[module_name]
    default  = getattr(module, 'DefaultDict', None)

    if filename is None:
        try:
            filename = bliss.config[config_key].filename
        except (AttributeError, KeyError), e:
            bliss.log.error('Missing "%s.filename" in config.yaml', config_key)

    if filename is not None and (default is None or reload is True):
        try:
            default = bliss.util.ObjectCache(filename, loader).load()
            setattr(module, 'DefaultDict', default)
        except IOError, e:
            msg = 'Could not load default %s "%s": %s'
            bliss.log.error(msg, config_key, filename, str(e))

    return default or { }


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


def toRepr (obj):
    """toRepr(obj) -> string

    Converts the Python object to a string representation of the kind
    often returned by a class __repr__() method.
    """
    args  = [ ]
    names = [ ]

    if hasattr(obj, "__dict__"):
        names = getattr(obj, "__dict__").keys()
    elif hasattr(obj, "__slots__"):
        names = getattr(obj, "__slots__")

    for name in names:
        value = getattr(obj, name)
        if value is not None:
            if type(value) is str:
                if len(value) > 32:
                    value = value[0:32] + "..."
                value = "'" + value + "'"
        args.append("%s=%s" % (name, str(value)))

    return "%s(%s)" % (obj.__class__.__name__, ", ".join(args))


def toDict(obj):
  """toDict(obj) -> string

  Converts the Python object to a dictionary object
  """
  args  = []
  attrs = []

  data = {}

  if hasattr(obj, "__dict__"):
    attrs = getattr(obj, "__dict__").keys()
  elif hasattr(obj, "__slots__"):
    attrs = getattr(obj, "__slots__")
  else:
    return obj
  
  for attr in attrs:
    value = getattr(obj, attr)
    key = attr[1:] if attr.startswith("_") else attr

    # FIXME: This is a hacky fix for the issue of when clauses being serialized
    # with the code expression included, which breaks json.dumps. This all needs
    # to be handled in a cleaner way.
    if key == 'when':
        data[key] = str(obj)
        return data

    if value is not None:
      if isinstance(value, (list, tuple, set)) and len(value) > 0:
        # Check the first object in the list to see if it is primitive
        if not isinstance(value[0], (str, basestring, int, long, float, complex)):
          retval = {}
          for k, v in enumerate(value):
            o = toDict(v)
            if type(o) is dict and 'name' in o.keys():
              retval.update({o['name']: o})
            else:
              retval.update({k: o})
        else: 
          # Otherwise, just return the list
          retval = value
      elif isinstance(value, dict):
        retval = {}
        for k, v in value.items():
          retval.update({str(k): toDict(v)})
      elif not isinstance(value, (str, basestring, int, long, float, complex)):
        try:
          retval = value.toDict()
        except:
          retval = toDict(value)
      else:
        retval = value

      data[key] = retval

  return data


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


if __name__ == "__main__":
    # HACK: The 'doctest' module imports 'pdb' which imports 'cmd'.
    # Since none of these modules are using Python absolute imports, The
    # Python 'cmd' module conflicts with 'bliss.cmd' (in this directory).
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
