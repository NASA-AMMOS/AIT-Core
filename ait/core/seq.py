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
AIT Sequences

The ait.core.seq module provides sequences of commands.
"""

from __future__ import absolute_import

import os
import math
import struct
import sys
import time

from ait.core import cmd, util


def setBit (value, bit, bitval):
  """Returns value with a specific bit position set to bitval."""
  if bitval:
    return value |  (1 << bit)
  else:
    return value & ~(1 << bit)



class Seq (object):
  """Seq - Sequence

  """
  Magic = 0x0C03


  def __init__ (self, pathname=None, cmddict=None, id=None, version=0):
    """Creates a new AIT Command Sequence

    Creates an empty sequence which will be encoded and decoded based
    on the given command dictionary (default: cmd.DefaultCmdDict).  If
    the optional pathname is given, the command sequence (text or
    binary) will be read from it.
    """
    self.pathname  = pathname
    self.cmddict   = cmddict or cmd.getDefaultCmdDict()
    self.crc32     = None
    self.seqid     = int(id)
    self.lines     = [ ]
    self.header    = { }
    self.version   = version
    self.log       = SeqMsgLog()

    if self.pathname is not None:
      self.read()


  def _parseHeader (self, line, lineno, log):
    """Parses a sequence header line containing 'name: value' pairs."""
    if line.startswith('#') and line.find(':') > 0:
      tokens = [ t.strip().lower() for t in line[1:].split(":", 1) ]
      name   = tokens[0]
      pos    = SeqPos(line, lineno)

      if name in self.header:
        msg = 'Ignoring duplicate header parameter: %s'
        log.warning(msg % name, pos)
      else:
        for expected in ['seqid', 'version']:
          if name == expected:
            value = util.toNumber(tokens[1], None)
            if value is None:
              msg = 'Parameter "%s" value "%s" is not a number.'
              log.error(msg % (name, tokens[1]), poss)
            else:
              self.header[name] = value


  @property
  def cmddict (self):
    """The command dictionary used to encode and decode this sequence."""
    return self._cmddict


  @cmddict.setter
  def cmddict (self, value):
    if value is None:
      value = cmd.getDefaultCmdDict()
    self._cmddict = value


  @property
  def commands (self):
    """The ordered list of SeqCmds in this sequence."""
    return filter(lambda line: type(line) is SeqCmd, self.lines)


  @property
  def duration (self):
    """The total duration of this sequence."""
    return sum(cmd.delay.delay for cmd in self.commands)


  @property
  def binpath (self):
    """The full path to the binary sequence filename."""
    return self._basepath + '.bin'


  @property
  def pathname (self):
    """The underlying sequence pathname."""
    return self._pathname


  @pathname.setter
  def pathname (self, pathname):
    self._pathname = None
    self._basepath = None
    self._basename = None

    if pathname is not None:
      self._pathname = pathname
      self._basepath = os.path.splitext(self._pathname)[0]
      self._basename = os.path.basename(self._basepath)


  @property
  def txtpath (self):
    """The full path to the text sequence filename."""
    return self._basepath + '.txt'


  def append (self, cmd, delay=0.000, attrs=None):
    """Adds a new command with a relative time delay to this sequence."""
    self.lines.append( SeqCmd(cmd, delay, attrs) )


  def printText (self, stream=None):
    """Prints a text representation of this sequence to the given stream or
    standard output.
    """
    if stream is None:
      stream = sys.stdout

    stream.write('# seqid   : %u\n'     % self.seqid         )
    stream.write('# version : %u\n'     % self.version       )
    stream.write('# crc32   : 0x%04x\n' % self.crc32         )
    stream.write('# ncmds   : %u\n'     % len(self.commands) )
    stream.write('# duration: %.3fs\n'  % self.duration      )
    stream.write('\n')

    for line in self.lines:
      stream.write( str(line) )
      stream.write('\n')


  def read (self, filename=None):
    """Reads a command sequence from the given filename (defaults to
    self.pathname).
    """
    if filename is None:
      filename = self.pathname

    stream = open(filename, 'rb')
    magic  = struct.unpack('>H', stream.read(2))[0]
    stream.close()

    if magic == Seq.Magic:
      self.readBinary(filename)
    else:
      self.readText(filename)


  def readBinary (self, filename=None):
    """Reads a binary command sequence from the given filename (defaults to
    self.pathname).
    """
    if filename is None:
      filename = self.pathname

    stream       = open(filename, 'rb')
    magic        = struct.unpack('>H', stream.read(2))[0]
    self.crc32   = struct.unpack('>I', stream.read(4))[0]
    self.seqid   = struct.unpack('>H', stream.read(2))[0]
    self.version = struct.unpack('>H', stream.read(2))[0]
    ncmds        = struct.unpack('>H', stream.read(2))[0]
    reserved     = stream.read(20)

    for n in range(ncmds):
      bytes = stream.read(110)
      self.lines.append( SeqCmd.decode(bytes, self.cmddict) )


  def readText (self, filename=None):
    """Reads a text command sequence from the given filename (defaults to
    self.pathname).
    """
    if filename is None:
      filename = self.pathname

    self.header = { }
    inBody      = False

    with open(filename, 'rt') as stream:
      for (lineno, line) in enumerate(stream.readlines()):
        stripped = line.strip()
        if stripped == '':
          continue
        elif stripped.startswith('#'):
          if not inBody:
            self._parseHeader(line, lineno, self.log)
        else:
          inBody = True
          self.lines.append( SeqCmd.parse(line, lineno, self.log, self.cmddict) )

    if 'seqid' in self.header:
      self.seqid = self.header['seqid']
    elif self.seqid is None:
      self.log.error('No sequence id present in header.')

    if 'version' in self.header:
      self.version = self.header['version']
    elif self.version is None:
      self.log.warning('No version present in header.  Defaulting to zero (0).')
      self.version = 0


  def validate (self):
    """Returns True if this Sequence is valid, False otherwise.
    Validation error messages are stored in self.messages.
    """
    if not os.path.isfile(self.pathname):
      self.message.append('Filename "%s" does not exist.')
    else:
      try:
        with open(self.pathname, 'r') as stream:
          pass
      except IOError:
        self.messages.append('Could not open "%s" for reading.' % self.pathname)

    for line in self.commands:
      messages = [ ]
      if line.cmd and not line.cmd.validate(messages):
        msg = 'error: %s: %s' % (line.cmd.name, " ".join(messages))
        self.log.messages.append(msg)

    return len(self.log.messages) == 0


  def writeBinary (self, filename=None):
    """Writes a binary representation of this sequence to the given filename
    (defaults to self.binpath).
    """
    if filename is None:
      filename = self.binpath

    with open(filename, 'wb') as output:
      # Magic Number
      output.write( struct.pack('>H', Seq.Magic          )  )
      # Upload Type
      output.write( struct.pack('B', 9                   )  )
      # Version
      output.write( struct.pack('B', self.version        )  )
      # Number of Commands
      output.write( struct.pack('>H', len(self.commands) )  )
      # Sequence ID
      output.write( struct.pack('>H', self.seqid         )  )
      # CRC Placeholder
      output.write( struct.pack('>I', 0                  ) )

      pad = struct.pack('B', 0)
      for n in range(20):
        output.write(pad)

      for line in self.lines:
        output.write( line.encode() )

    self.crc32 = util.crc32File(filename, 0)

    with open(filename, 'r+b') as output:
      output.seek(28)
      output.write( struct.pack('>I', self.crc32) )


  def writeText (self, filename=None):
    """Writes a text representation of this sequence to the given filename
    (defaults to self.txtpath).
    """
    if filename is None:
      filename = self.txtpath

    with open(filename, 'wt') as output:
      self.printText(output)



class SeqPos (object):
  """SeqPos - Sequence Position

  Each SeqAtom contains a SeqPos to locate the atom within the text
  sequence.
  """

  def __init__ (self, line=None, lineno=1, start=1, stop=None):
    """Creates a new SeqPos from the given line in the sequence and start
    and stop line and character positions within the line.
    """
    if line is None:
      line  = ''
      start = 0
      stop  = 0

    self.line   = line
    self.lineno = lineno
    self.col    = slice(start, stop or len(self.line))


  def __str__ (self):
    """Returns this SeqPos as a string."""
    return str(self.lineno) + ':' + str(self.col.start) + ':'



class SeqAtom (object):
  """SeqAtom - Sequence Atom

  Sequence atoms are the smallest unit of a sequence.  This class
  serves as a base class for specific parts of a sequence,
  e.g. header, comments, commands, attributes, and meta-commands.
  """

  def __init__ (self, pos=None):
    """Creates a new SeqAtom with the given SeqPos."""
    self.pos = pos or SeqPos()


  def __str__ (self):
    """Returns this SeqAtom as a string."""
    result = ''
    if len(self.pos.line) is not None:
      result = self.pos.line[self.pos.col.start - 1:self.pos.col.stop]
    return result


  @classmethod
  def decode (cls, bytes, cmddict=None):
    """Decodes an SeqAtom from an array of bytes, according to the given
    command dictionary, and returns a new SeqAtom.
    """
    return cls()


  def encode (self):
    """Encodes this SeqAtom to binary and returns a bytearray."""
    return bytearray()


  @classmethod
  def parse (cls, line, lineno, log, cmddict=None):
    """Parses the SeqAtom from a line of text, according to the given
    command dictionary, and returns a new SeqAtom or None.  Warning
    and error messages are logged via the SeqMsgLog log.
    """
    return cls(line)


  def validate (self, log):
    """Returns True if this SeqAtom is valid, False otherwise.  Warning
    and error messages are logged via the SeqMsgLog log.
    """
    return True



class SeqCmd (SeqAtom):
  """SeqCmd - Sequence Command

  Each SeqCmd contains a command, a relative time delay, and command
  attributes.  New SeqCmds may be created with an explicit cmd.Cmd and
  decimal delay (SeqCmd()), via an array of bytes (decode()), or a
  line of text (parse()).
  """

  def __init__ (self, cmd, delay=0.000, attrs=None, comment=None, pos=None):
    """Creates a new SeqCmd."""
    super(SeqCmd, self).__init__(pos)
    self.cmd     = cmd
    self.delay   = delay
    self.attrs   = attrs
    self.comment = comment


  def __str__ (self):
    s = '%s\t%s' % (str(self.delay), str(self.cmd))

    if self.attrs:
      s += '\t%s' % str(self.attrs)

    if self.comment:
      s += '\t%s' % str(self.comment)

    return s


  @classmethod
  def decode (cls, bytes, cmddict):
    """Decodes a sequence command from an array of bytes, according to the
    given command dictionary, and returns a new SeqCmd.
    """
    attrs = SeqCmdAttrs.decode(bytes[0:1])
    delay = SeqDelay   .decode(bytes[1:4])
    cmd   = cmddict    .decode(bytes[4:] )
    return cls(cmd, delay, attrs)


  def encode (self):
    """Encodes this SeqCmd to binary and returns a bytearray."""
    return self.attrs.encode() + self.delay.encode() + self.cmd.encode()


  @classmethod
  def parse (cls, line, lineno, log, cmddict):
    """Parses the sequence command from a line of text, according to the
    given command dictionary, and returns a new SeqCmd.
    """
    delay   = SeqDelay   .parse(line, lineno, log, cmddict)
    attrs   = SeqCmdAttrs.parse(line, lineno, log, cmddict)
    comment = SeqComment .parse(line, lineno, log, cmddict)
    stop    = len(line)

    if comment:
      stop = comment.pos.col.start - 1

    if attrs and attrs.pos.col.start != -1:
      stop = attrs.pos.col.start - 1

    tokens = line[:stop].split()
    name   = tokens[1]
    args   = tokens[2:]
    start  = line.find(name)
    pos    = SeqPos(line, lineno, start + 1, stop)

    if name not in cmddict:
      log.error('Unrecognized command "%s".' % name, pos)
    elif cmddict[name].nargs != len(args):
      msg = 'Command argument size mismatch: expected %d, but encountered %d.'
      log.error(msg % (cmddict[name].nargs, len(args)), pos)

    args   = [ util.toNumber(a, a) for a in args ]
    cmd    = cmddict.create(name, *args)

    return cls(cmd, delay, attrs, comment, pos)



class SeqCmdAttrs (SeqAtom):
  """SeqCmdAttrs - Sequence Command Attributes

  Each sequence command may be annotated with attributes following the
  command by using the following syntax:

    { name: value, ... }

  """

  Table = [
  #   Bit   Name          Value0     Value1       Default
  #   ---  -------------  --------   -----------  ---------
    [  7,  'OnError'   ,  'Halt'  ,  'Continue',  'Halt'    ],
    [  6,  'Attribute6',  'Value0',  'Value1'  ,  'Value0'  ],
    [  5,  'Attribute5',  'Value0',  'Value1'  ,  'Value0'  ],
    [  4,  'Attribute4',  'Value0',  'Value1'  ,  'Value0'  ],
    [  3,  'Attribute3',  'Value0',  'Value1'  ,  'Value0'  ],
    [  2,  'Attribute2',  'Value0',  'Value1'  ,  'Value0'  ],
    [  1,  'Attribute1',  'Value0',  'Value1'  ,  'Value0'  ],
    [  0,  'Attribute0',  'Value0',  'Value1'  ,  'Value0'  ]
  ]


  def __init__ (self, attrs=None, pos=None):
    """Creates a new SeqCmdAttrs."""
    super(SeqCmdAttrs, self).__init__(pos)
    self.attrs = attrs or { }


  def __str__ (self):
    """Returns this SeqCmdAttrs as a string."""
    if len(self.attrs) > 0:
      return '{ %s }' % ', '.join(': '.join(item) for item in self.attrs.items())
    else:
      return ''


  @property
  def default (self):
    """The default sequence command attributes (as an integer)."""
    byte = 0
    for bit, name, value0, value1, default in SeqCmdAttrs.Table:
      if default == value1:
        byte = setBit(byte, bit, 1)
    return byte


  @classmethod
  def decode (cls, bytes, cmddict=None):
    """Decodes sequence command attributes from an array of bytes and
    returns a new SeqCmdAttrs.
    """
    byte   = struct.unpack('B', bytes)[0]
    self   = cls()
    defval = self.default

    for bit, name, value0, value1, default in SeqCmdAttrs.Table:
      mask   = 1 << bit
      bitset = mask & byte
      defset = mask & defval
      if bitset != defset:
        if bitset:
          self.attrs[name] = value1
        else:
          self.attrs[name] = value0

    return self


  def encode (self):
    """Encodes this SeqCmdAttrs to binary and returns a bytearray."""
    byte = self.default

    for bit, name, value0, value1, default in SeqCmdAttrs.Table:
      if name in self.attrs:
        value = self.attrs[name]
        byte  = setBit(byte, bit, value == value1)

    return struct.pack('B', byte)


  @classmethod
  def parse (cls, line, lineno, log, cmddict=None):
    """Parses a SeqCmdAttrs from a line of text and returns it or None.
    Warning and error messages are logged via the SeqMsgLog log.
    """
    start  = line.find('{')
    stop   = line.find('}')
    pos    = SeqPos(line, lineno, start + 1, stop)
    result = cls(None, pos)

    if start >= 0 and stop >= start:
      attrs = { }
      pairs = line[start + 1:stop].split(',')

      for item in pairs:
        ncolons = item.count(':')
        if ncolons == 0:
          log.error('Missing colon in command attribute "%s".' % item, pos)
        elif ncolons > 1:
          log.error('Too many colons in command attribute "%s".' % item, pos)
        else:
          name, value = (s.strip() for s in item.split(':'))
          attrs[name] = value

      result = cls(attrs, pos)

    elif start != -1 or stop != -1:
      log.error('Incorrect command attribute curly brace placement.', pos)

    return result



class SeqComment (SeqAtom):
  """SeqComment - Sequence Comment

  Sequence comments are parsed for completeness, but are ignored when
  translating a sequence to its binary representation.
  """

  def __init__ (self, comment, pos=None):
    """Creates a new SeqComment."""
    super(SeqComment, self).__init__(pos)
    self.comment = comment



  @classmethod
  def parse (cls, line, lineno, log, cmddict=None):
    """Parses the SeqComment from a line of text.  Warning and error
    messages are logged via the SeqMsgLog log.
    """
    start  = line.find('#')
    pos    = SeqPos(line, lineno, start + 1, len(line))
    result = None

    if start >= 0:
      result = cls(line[start:], pos)

    return result


class SeqDelay (SeqAtom):
  """SeqDelay - Sequence Delay

  Sequence lines begin with a decimal relative time delay.
  """

  def __init__ (self, delay=0.000, pos=None):
    """Creates a new SeqDelay with the given relative time delay."""
    super(SeqDelay, self).__init__(pos)
    self.delay = delay


  def __str__ (self):
    """Returns this SeqDelay as a string."""
    return '%.3f' % self.delay


  @classmethod
  def decode (cls, bytes, cmddict=None):
    """Decodes a sequence delay from an array of bytes, according to the
    given command dictionary, and returns a new SeqDelay.
    """
    delay_s  = struct.unpack('>H', bytes[0:2])[0]
    delay_ms = struct.unpack('B' , bytes[2:3])[0]
    return cls(delay_s + (delay_ms / 255.0))


  def encode (self):
    """Encodes this SeqDelay to a binary bytearray."""
    delay_s  = int( math.floor(self.delay) )
    delay_ms = int( (self.delay - delay_s) * 255.0 )
    return struct.pack('>H', delay_s) + struct.pack('B', delay_ms)


  @classmethod
  def parse (cls, line, lineno, log, cmddict=None):
    """Parses the SeqDelay from a line of text.  Warning and error
    messages are logged via the SeqMsgLog log.
    """
    delay = -1
    token = line.split()[0]
    start = line.find(token)
    pos   = SeqPos(line, lineno, start + 1, start + len(token))

    try:
      delay = float(token)
    except ValueError:
      msg = 'String "%s" could not be interpreted as a numeric time delay.'
      log.error(msg % token, pos)

    return cls(delay, pos)


  def validate (self, log):
    """Returns True if this SeqDelay is valid, False otherwise.  Warning
    and error messages are logged via the SeqMsgLog log.
    """
    return self.delay >= 0



class SeqMetaCmd (SeqAtom):
  """SeqMetaCmd - Sequence Meta-Command

  Sequence meta-commands are parsed and executed locally, but are
  ignored when translating a sequence to its binary representation.
  """

  def __init__ (self, metacmd, pos=None):
    """Creates a new SeqMetaCmd."""
    super(SeqMetaCmd, self).__init__(pos)
    self.metacmd = metacmd


  @classmethod
  def parse (cls, line, lineno, log, cmddict=None):
    """Parses the SeqMetaCmd from a line of text.  Warning and error
    messages are logged via the SeqMsgLog log.
    """
    start  = line.find('%')
    pos    = SeqPos(line, lineno, start + 1, len(line))
    result = None

    if start >= 0:
      result = cls(line[start:], pos)

    return result



class SeqMsgLog (object):
  """SeqMsgLog - Sequence Message Log

  SeqMsgLog logs warning and errors encountered during sequence
  parsing and validation.
  """

  def __init__ (self, filename=None):
    """Creates a new SeqMsgLog pertaining to the given sequence filename."""
    self.messages = [ ]
    self.filename = filename


  def error (self, msg, pos=None):
    """Logs an error message pertaining to the given SeqPos."""
    self.log(msg, 'error: ' + self.location(pos))


  def location (self, pos):
    """Formats the location of the given SeqPos as:

        filename:line:col:
    """
    result = ''
    if self.filename:
      result += self.filename + ':'
    if pos:
      result += str(pos)
    return result


  def log (self, msg, prefix=None):
    """Logs a message with an optional prefix."""
    if prefix:
      if not prefix.strip().endswith(':'):
        prefix += ': '
      msg = prefix + msg
    self.messages.append(msg)


  def warning (self, msg, pos=None):
    """Logs a warning message pertaining to the given SeqAtom."""
    self.log(msg, 'warning: ' + self.location(pos))
