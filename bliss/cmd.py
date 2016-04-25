"""
BLISS (ECOSTRESS) Commands

The bliss.cmd module provides commands and command dictionaries.
Dictionaries contain command and argument definitions.
"""

"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import os
import struct
import yaml

import bliss


MAX_CMD_WORDS = 54


class ArgDefn(object):
    """ArgDefn - Argument Definition

    Argument Definitions encapsulate all information required to define
    a single command argument.  This includes the argument name, its
    description, units, type, byte position within a command, name-value
    enumerations, and allowed value ranges.  Name, type, and byte
    position are required.  All others are optional.

    A fixed argument (fixed=True) defines a fixed bit pattern in that
    argument's byte position(s).
    """
    __slots__ = [
        "name", "desc", "units", "_type", "bytes", "_enum", "range",
        "fixed", "value"
    ]

    def __init__(self, *args, **kwargs):
        """Creates a new Argument Definition.
        """
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))

    def __repr__(self):
        return bliss.util.toRepr(self)

    @property
    def enum(self):
        """The argument enumeration."""
        return self._enum

    @enum.setter
    def enum(self, value):
        self._enum = None
        if value is not None:
            self._enum = dict(reversed(pair) for pair in value.items())

    @property
    def nbytes(self):
        """The number of bytes required to encode this argument."""
        return self.type.nbytes

    @property
    def type(self):
        """The argument type."""
        return self._type

    @type.setter
    def type(self, value):
        self._type = bliss.dtype.get(value) if type(value) is str else value

    @property
    def startword(self):
        """The argument start word in the command"""
        return self.slice().start / 2 + 1

    @property
    def startbit(self):
        """The argument start bit in the word"""
        return self.slice().start % 2 * 8

    def decode(self, bytes):
        """Decodes the given bytes according to this BLISS Argument
        Definition.
        """
        value = self.type.decode(bytes)
        if self._enum is not None:
            for name, val in self._enum.items():
                if value == val:
                    value = name
                    break
        return value

    def encode(self, value):
        """Encodes the given value according to this BLISS Argument
        Definition.
        """
        if type(value) == str and self.enum and value in self.enum:
            value = self.enum[value]
        return self.type.encode(value) if self.type else bytearray()

    def slice(self, offset=0):
        """Returns a Python slice object (e.g. for array indexing) indicating
        the start and stop byte position of this Command argument.  The
        start and stop positions may be translated by the optional byte
        offset.
        """
        if type(self.bytes) is int:
            start = self.bytes
            stop  = start + 1
        else:
            start = self.bytes[0]
            stop  = self.bytes[1] + 1

        return slice(start + offset, stop + offset)

    def validate(self, value, messages=None):
        """Returns True if the given Argument value is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        valid     = True
        primitive = value

        def log(msg):
            if messages is not None:
                messages.append(msg)

        if self.enum:
            if value not in self.enum.keys():
                valid = False
                args  = (self.name, str(value))
                log("%s value '%s' not in allowed enumerated values." % args)
            else:
                primitive = int(self.enum[value])

        if self.type:
            if self.type.validate(primitive, messages, self.name) is False:
                valid = False

        if self.range:
            if primitive < self.range[0] or primitive > self.range[1]:
                valid = False
                args  = (self.name, str(primitive), self.range[0], self.range[1])
                log("%s value '%s' out of range [%d, %d]." % args)

        return valid

    def toDict(self):
        return {self.name: bliss.util.toDict(self)}


class Cmd(object):
    """Cmd - Command

    Commands reference their Command Definition and may contain arguments.
    """
    def __init__(self, defn, *args):
        """Creates a new BLISS Command based on the given command definition
        and command arguments.
        """
        self.defn = defn
        self.args = args

    def __repr__(self):
        return self.defn.name + " " + " ".join([str(a) for a in self.args])

    @property
    def desc(self):
        """The command description."""
        return self.defn.desc

    @property
    def name(self):
        """The command name."""
        return self.defn.name

    @property
    def opcode(self):
        """The command opcode."""
        return self.defn.opcode

    @property
    def subsystem(self):
        """The subsystem to which this command applies."""
        return self.defn.subsystem

    @property
    def argdefns(self):
        """The command argument definitions."""
        return self.defn.argdefns

    def encode(self, pad=106):
        """Encodes this BLISS command to binary.

        If pad is specified, it indicates the maximum size of the encoded
        command in bytes.  If the encoded command is less than pad, the
        remaining bytes are set to zero.

        Commands sent to ISS payloads over 1553 are limited to 64 words
        (128 bytes) with 11 words (22 bytes) of CCSDS overhead (SSP
        52050J, Section 3.2.3.4).  This leaves 53 words (106 bytes) for
        the command itself.
        """
        offset  = len(self.defn.opcode)
        size    = max(offset + self.defn.argsize, pad)
        encoded = bytearray(size)

        encoded[0:offset] = self.defn.opcode
        encoded[offset]   = self.defn.argsize
        offset           += 1
        index             = 0

        for defn in self.defn.argdefns:
            if defn.fixed:
                value = defn.value
            else:
                value  = self.args[index]
                index += 1
            encoded[defn.slice(offset)] = defn.encode(value)

        return encoded

    def validate(self, messages=None):
        """Returns True if the given Command is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        return self.defn.validate(self, messages)

    def toDict(self):
        return self.defn.toDict()


class CmdDefn(object):
    """CmdDefn - Command Definition

    Command Definitions encapsulate all information required to define a
    single command.  This includes the command name, its opcode,
    subsystem, description and a list of argument definitions.  Name and
    opcode are required.  All others are optional.
    """
    __slots__ = ["name", "_opcode", "subsystem", "title", "desc", "argdefns"]


    def __init__(self, *args, **kwargs):
        """Creates a new Command Definition."""
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, slot, kwargs.get(name, None))

        if self.argdefns is None:
            self.argdefns = []


    def __repr__(self):
        return bliss.util.toRepr(self)

    @property
    def nargs(self):
        """The number of arguments to this command (excludes fixed arguments)."""
        return len(filter(lambda d: not d.fixed, self.argdefns))

    @property
    def nbytes(self):
        """The number of bytes required to encode this command.

        Encoded commands are comprised of a two byte opcode, followed by a
        one byte size, and then the command argument bytes.  The size
        indicates the number of bytes required to represent command
        arguments.
        """
        return len(self.opcode) + 1 + sum(arg.nbytes for arg in self.argdefns)

    @property
    def opcode(self):
        """Returns the opcode for the given command."""
        return bytearray(struct.pack(">H", self._opcode))

    @property
    def argsize(self):
        """The total size in bytes of all the command arguments."""
        argsize = sum(arg.nbytes for arg in self.argdefns)
        return argsize if len(self.argdefns) > 0 else 0

    def staging_required(self):
        maxbytes = getMaxCmdSize()
        if self.argsize > maxbytes:
            msg = "Command %s larger than %d bytes. Staging required."
            bliss.log.debug(msg, self.name, maxbytes)
            return False
        else:
            return True

    def validate(self, cmd, messages=None):
        """Returns True if the given Command is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        valid    = True
        argdefns = [defn for defn in self.argdefns if not defn.fixed]

        if len(argdefns) != len(cmd.args):
            valid = False
            if messages is not None:
                msg  = "Argument number mismatch for command '%s'.  "
                msg += "Expected %d, but received %d."
                messages.append(msg % (self.name, len(self.argdefns), len(cmd.args)))

        for defn, value in zip(argdefns, cmd.args):
            if defn.validate(value, messages) is False:
                valid = False

        return valid

    def toDict(self):
        return { self._opcode: bliss.util.toDict(self) }


class CmdDict(dict):
    """CmdDict

    Command Dictionaries provide a Python dictionary (i.e. hashtable)
    interface mapping Command names to Command Definitions.
    """
    def __init__(self, *args, **kwargs):
        """Creates a new Command Dictionary from the given command dictionary
        filename.
        """
        self.filename = None
        self.opcodes  = {}

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add(self, defn):
        """Adds the given Command Definition to this Command Dictionary."""
        self[defn.name]            = defn
        self.opcodes[defn._opcode] = defn


    def create(self, name, *args):
        """Creates a new BLISS command with the given arguments."""
        cmd  = None
        defn = self.get(name, None)
        if defn:
            cmd = Cmd(defn, *args)
        return cmd

    def decode(self, bytes):
        """Decodes the given bytes according to this BLISS Command
        Definition.
        """
        opcode  = struct.unpack(">H", bytes[0:2])[0]
        nbytes  = struct.unpack("B",  bytes[2:3])[0]
        name   = None
        args   = []

        if opcode in self.opcodes:
            defn = self.opcodes[opcode]
            name = defn.name
            stop = 3

            for arg in defn.argdefns:
                start = stop
                stop  = start + arg.nbytes
                if arg.fixed:
                    pass  # FIXME: Confirm fixed bytes are as expected?
                else:
                    args.append(arg.decode(bytes[start:stop]))

        return self.create(name, *args)

    def load(self, filename):
        """Loads Command Definitions from the given YAML file into this
        Command Dictionary.
        """
        if self.filename is None:
            self.filename = filename
        with open(self.filename, 'rb') as stream:
            for cmd in yaml.load_all(stream):
                self.add(cmd)

    def toDict(self):
        data = {}
        for name, val in self.opcodes.items():
            data.update(val.toDict())

        return data


def getDefaultDict(reload=False):
    return bliss.util.getDefaultDict(__name__, 'cmddict', CmdDict, reload)


def getDefaultSchema():
    return os.path.join(bliss.Config.CONFIG_DIR, 'cmd_schema.json')


def getMaxCmdSize():
    """ Returns the maximum size TReK command in bytes

    Converts from words to bytes (hence the *2) and
    removes 1 word for CCSDS header (-1)
    """
    return (MAX_CMD_WORDS - 1) * 2


def YAMLCtor_ArgDefn(loader, node):
    fields          = loader.construct_mapping(node, deep=True)
    fields["fixed"] = node.tag == "!Fixed"
    return ArgDefn(**fields)


def YAMLCtor_CmdDefn(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    fields['argdefns'] = fields.pop('arguments', None)
    return CmdDefn(**fields)

yaml.add_constructor('!Command' , YAMLCtor_CmdDefn)
yaml.add_constructor('!Argument', YAMLCtor_ArgDefn)
yaml.add_constructor('!Fixed'   , YAMLCtor_ArgDefn)
