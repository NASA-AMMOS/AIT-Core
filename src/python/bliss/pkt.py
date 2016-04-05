#!/usr/bin/env python

"""
BLISS Packet

The bliss.pkt module provides a representation for packet data.
Packet raw binary data is accessible as bytes, words, or high-level
field names (via the FldDefn class).

No attempt is made to encode (pack) or decode (unpack) fields until
specifically requested.  This lazy evaluation makes specialized packet
processors particularly efficient as time and effort is only spent to
pack and unpack data that is absolutely necessary.

Command packets are read from cmd.yaml.  Eventually, we'd like
telemetry packet definitions to be read from tlm.yaml.  Until then,
subclasses of pkt.Pkt should use the FldMap decorator and define a
FieldList, e.g.:

  @pkt.FldMap
  class MyPkt (pkt.Pkt):
    FieldList = [
      pkt.FldDefn( "version"      ,   0, "B"   , 0b11100000         ),
      pkt.FldDefn( "type"         ,   0, "B"   , 0b00010000         ),
      pkt.FldDefn( "secondary"    ,   0, "B"   , 0b00001000         ),
      pkt.FldDefn( "apid"         ,   0, ">H"  , 0b0000011111111111 ),
      pkt.FldDefn( "seqflags"     ,   2, "B"   , 0b11000000         ),
      pkt.FldDefn( "seqcount"     ,   2, ">H"  , 0b0011111111111111 ),
      pkt.FldDefn( "length"       ,   4, ">H"                       ),
    ]

"""

"""
Authors: Erik Hovland, Jordan Padams, Ben Bornstein

Copyright 2014 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import struct


class wordarray (object):
  """Wordarrays are somewhat analogous to Python bytearrays, but
  currently much more limited in functionality.  They provide a
  readonly view of a bytearray addressable and iterable as a sequence
  of 16-bit words.  This is convenient for telemetry processing as
  packets are often more naturally addressable on word, as opposed to
  byte, boundaries.
  """


  def __init__ (self, bytes):
    """Creates a new wordarray from the given bytearray.

    The given bytearray should contain an even number of bytes.  If
    odd, the last byte is ignored.
    """
    self._bytes = bytes


  def __getitem__ (self, key):
    """Returns the words in this wordarray at the given Python slice
    or word at the given integer index."""
    length = len(self)

    if isinstance(key, slice):
      return [ self[n] for n in xrange(*key.indices(length)) ]

    elif isinstance(key, int):
      if key < 0:
        key += length
      if key >= length:
        msg = "wordarray index (%d) is out of range [0 %d]."
        raise IndexError(msg % (key, length - 1))
      index = 2 * key
      return (self._bytes[index] << 8) | self._bytes[index + 1]

    else:
      raise TypeError("wordarray indices must be integers.")


  def __len__ (self):
    """Returns the number of words in this wordarray."""
    return len(self._bytes) / 2



class FldDefn (object):
  """FldDefn - Field Definition

  Field Definitions encapsulate all information required to define a
  single packet field.  This includes the field name, byte offset, its
  format, and an optional bitmask.

  Use the get() and set() methods to extract and set a field's value
  in the underlying raw packet data.
  """


  def __init__ (self, name, offset, format=None, mask=None):
    """Creates a new FldDefn from the given offset, format, and
    optional conversion object.
    """
    self._name   = name
    self._offset = offset
    self._mask   = mask
    self._shift  = 0

    if isinstance(format, Pkt):
      self._packet = format
      self._struct = None
    else:
      self._packet = None
      self._struct = struct.Struct(format)

    if mask is not None:
      while mask != 0 and mask & 1 == 0:
        self._shift +=  1
        mask        >>= 1


  @property
  def name (self):
    """This packet field's name."""
    return self._name


  @property
  def nbytes (self):
    """The number of bytes required to represent this packet field."""
    return self._struct.size if self._struct else self._packet.nbytes


  @property
  def offset (self):
    """This packet field's start byte offset."""
    return self._offset


  @offset.setter
  def offset (self, offset):
    self._offset = offset


  @property
  def start (self):
    """This packet field's start byte offset."""
    return self.offset


  @property
  def stop (self):
    """This packet field's stop byte offset."""
    return self.offset + self.nbytes


  def get (self, data):
    """Returns this field's value from the underlying raw packet data."""
    if self._packet:
      value = self._packet
    else:
      bytes = data[ self.slice() ]

      if self._struct.format.endswith("s"):
        value = bytes
      else:
        value = self._struct.unpack(bytes)

        if len(value) == 1:
          value = value[0]

          if self._mask is not None:
            value &= self._mask

          if self._shift > 0:
            value >>= self._shift

    return value


  def set (self, data, value):
    """Sets this field's value in the underlying raw packet data."""
    if self._struct is None:
      return

    if self._struct.format.endswith("s"):
      data[ self.slice() ] = value
    else:
      bytes   = data[ self.slice() ]
      current = self._struct.unpack(bytes)

      if len(current) == 1:
        current = current[0]

        if self._shift > 0:
          value <<= self._shift

        if self._mask is not None:
          value   &= self._mask
          current &= ~self._mask
          value   |= current

        data[ self.slice() ] = bytearray( self._struct.pack(value) )

      else:
        data[ self.slice() ] = bytearray( self._struct.pack(*value) )


  def slice (self, offset=0):
    """Returns a Python slice object (e.g. for array indexing)
    indicating the start and stop byte position of this packet field.
    The start and stop positions may be translated by the optional
    byte offset.
    """
    return slice(self.start + offset, self.stop + offset)



def FldMap (cls):
  """Decorates a Pkt to create a class-level dictionary, FieldMap, to
  support fast lookup of packet field definitions (FldDefn) based on
  the field's name.

  If FieldMap were defined explicitly, the field's name would have to be
  repeated, e.g.:

    FieldMap = { "length": FldDefn("length", 4, ">H"), ... }

  or FldDefn would not have access to the field name, e.g.:

    FieldMap = { "length": FldDefn(4, ">H"), ... }

  Neither of which is particularly desirable.
  """
  if hasattr(cls, 'FieldList') and not hasattr(cls, 'FieldMap'):
    m = dict((defn.name, defn) for defn in getattr(cls, 'FieldList'))
    setattr(cls, 'FieldMap', m)
  return cls



class Pkt (object):
  """Pkt - Packet

  Packets contain their raw binary data, but make no attempt to encode
  (pack) or decode (unpack) it until specifically requested.  This
  lazy evaluation makes specialized packet processors particularly
  efficient as time and effort is only spent to pack and unpack data
  that is absolutely necessary.
  """

  def __init__ (self, data=None):
    """Creates a new packet containing the given raw packet data."""
    if data is None:
      data = bytearray(self.nbytes)

    if not isinstance(data, bytearray):
      data = bytearray(data)

    self._data = data


  def __len__ (self):
    """The length of the packet in bytes."""
    return len(self._data)


  def __getattr__ (self, name):
    """Returns the value of the given packet field name."""
    if name not in self.FieldMap:
      classname = self.__class__.__name__
      raise AttributeError("Packet %s has no field '%s'" % (classname, name))

    return self.FieldMap[name].get(self._data)


  def __setattr__ (self, name, value):
    """Sets the given packet field name to value."""
    if name not in self.FieldMap:
      object.__setattr__(self, name, value)
    else:
      self.FieldMap[name].set(self._data, value)


  @property
  def bytes (self):
    """Packet data as a bytearray."""
    return self._data


  @property
  def nbytes (self):
    """The size of this packet in bytes."""
    cls = self.__class__

    if not hasattr(cls, '_nbytes'):
      setattr(cls, '_nbytes', max(field.stop for field in self.FieldList))

    return cls._nbytes


  @property
  def words (self):
    """Packet data as a wordarray."""
    return wordarray(self._data)


  def write (self, stream):
    """Writes packet data to stream."""
    stream.write(self.bytes)
