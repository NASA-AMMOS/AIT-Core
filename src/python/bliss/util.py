#!/usr/bin/env python

"""
BLISS Utilities

The bliss.util module provides general utility functions.
"""

"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import os
import stat
import sys
import time
import zlib
import types

import bliss


if sys.platform == 'win32':
  # On Windows, the best timer is time.clock
  timer = time.clock
else:
  # On most other platforms the best timer is time.time
  timer = time.time


def crc32File (filename, skip=0):
  """Computes the CRC-32 of the contents of filename, optionally skipping
  a certain number of bytes at the beginning of the file.
  """
  with open(filename, "rb") as stream:
    discard = stream.read(skip)
    return zlib.crc32(stream.read()) & 0xffffffff


def endianSwapU16 (bytes):
  """Swaps pairs of bytes (16-bit words) in the given bytearray."""
  for b in range(0, len(bytes), 2):
    bytes[b], bytes[b + 1] = bytes[b + 1], bytes[b]
  return bytes


def getFileSize (filename):
  """Returns the size of filename in bytes."""
  return os.stat(filename)[stat.ST_SIZE]


def setDictDefaults (d, defaults):
  """Sets all defaults for the given dictionary to those contained in a
  second defaults dictionary.  This convenience method calls:

    d.setdefault(key, value)

  for each key and value in the given defaults dictionary.
  """
  for key, val in defaults.items():
    d.setdefault(key, val)

  return d


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

  Converts the given string to a floating-point value.  If the string
  could not be converted, default (None) is returned.

  NOTE: This method is *significantly* more effecient than toNumber()
  as it only attempts to parse floating-point numbers, not integers
  or hexadecimal numbers.

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
  """Returns a description of the given duration in the most
  appropriate units (e.g. seconds, ms, us, or ns)."""

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
