# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2015, by the California Institute of Technology. ALL RIGHTS
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
AIT Telemetry

The ait.core.tlm module provides telemetry fields and telemetry
dictionaries.  Dictionaries contain packet, header, data, and field
definitions.
"""

import collections
import os
import pkg_resources
import struct
import yaml
import csv

import ait
from ait.core import dtype, json, log, util


class wordarray(object):
    """Wordarrays are somewhat analogous to Python bytearrays, but
    currently much more limited in functionality.  They provide a
    readonly view of a bytearray addressable and iterable as a sequence
    of 16-bit words.  This is convenient for telemetry processing as
    packets are often more naturally addressable on word, as opposed to
    byte, boundaries.
    """

    __slots__ = [ '_bytes' ]


    def __init__(self, bytes):
        """Creates a new wordarray from the given bytearray.

        The given bytearray should contain an even number of bytes.  If
        odd, the last byte is ignored.
        """
        self._bytes = bytes

    def __getitem__(self, key):
        """Returns the words in this wordarray at the given Python slice
        or word at the given integer index."""
        length = len(self)

        if isinstance(key, slice):
            return [self[n] for n in xrange(*key.indices(length))]

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

    def __len__(self):
        """Returns the number of words in this wordarray."""
        return len(self._bytes) / 2



class DNToEUConversion(json.SlotSerializer, object):
    """DNToEUConversion
    """

    __slots__ = [ '_equation', 'units', '_when' ]

    def __init__(self, equation, units=None, when=None, terms=None):
        if when:
            when = PacketExpression(when)

        self._equation = PacketExpression(equation)
        self.units     = units
        self._when     = when


    def eval(self, packet):
        """Returns the result of evaluating this DNToEUConversion in the
        context of the given Packet.
        """
        result = None
        terms  = None

        if self._when is None or self._when.eval(packet):
            result = self._equation.eval(packet)

        return result



class FieldList(collections.Sequence):
    """FieldList

    FieldLists encapsulate a packet field array so that it behaves
    like a Python list (or more generally a sequence) when accessed.

    A FieldList should not be created directly.  It's created internally
    by the private Packet field accessor _getattr().
    """

    __slots__ = [ '_defn', '_packet', '_raw' ]

    def __init__(self, packet, defn, raw):
        self._packet = packet
        self._defn   = defn
        self._raw    = raw

    def __eq__ (self, other):
        return  (
            isinstance(other, collections.Sequence) and
            len(self) == len(other) and
            all(self[n] == other[n] for n in xrange(len(self)))
        )

    def __getitem__(self, key):
        return self._packet._getattr(self._defn.name, self._raw, key)

    def __len__(self):
        return self._defn.type.nelems



class FieldDefinition(json.SlotSerializer, object):
    """FieldDefinition

    FieldDefinitions encapsulate all information required to define a
    single packet field.  This includes the field name, byte offset,
    its format, and an optional bitmask.

    Use the get() and set() methods to extract and set a field's value
    in the underlying raw packet data.

    """

    __slots__ = [
        "_bytes", "desc", "dntoeu", "enum", "expr", "mask", "name", "shift",
        "_type", "units", "when", "_title", "aliases"
    ]

    def __init__(self, *args, **kwargs):
        """Creates a new FieldDefinition."""
        for slot in FieldDefinition.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))

        self.shift = 0

        # Set the shift based on the bitmask
        mask = self.mask
        if mask is not None:
            while mask != 0 and mask & 1 == 0:
                self.shift += 1
                mask >>= 1

        if self.dntoeu:
            self.dntoeu = createDNToEUConversion(**self.dntoeu)

        if self.expr:
            self.expr = createPacketExpression(self.expr)

        if self.when:
            self.when = createPacketExpression(self.when)


    def __jsonOmit__(self, key, val):
        return val is None or val is '' or (key == 'shift' and val == 0)

    def __repr__(self):
        return util.toRepr(self)


    @property
    def nbytes(self):
        """The number of bytes required to represent this packet field."""
        if type(self.type) is not str:
            return self.type.nbytes
        else:
            return 0

    @property
    def title(self):
        """The argument title."""
        if not self._title:
            return self.name
        else:
            return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def type(self):
        """The argument type."""
        return self._type

    @type.setter
    def type(self, value):
        if type(value) is str and dtype.get(value) is not None:
            self._type = dtype.get(value)
        else:
            self._type = value
            log.error("Invalid field type '%s' " % value)

    @property
    def bytes(self):
        """The argument bytes."""
        return self._bytes

    @bytes.setter
    def bytes(self, value):
        if type(value) is list and len(value) == 1:
            self._bytes = value[0]
        else:
            self._bytes = value


    def decode(self, bytes, raw=False, index=None):
        """Decodes the given bytes according to this Field Definition.

        If raw is True, no enumeration substitutions will be applied
        to the data returned.

        If index is an integer or slice (and the type of this
        FieldDefinition is an ArrayType), then only the element(s) at
        the specified position(s) will be decoded.
        """
        if index is not None and isinstance(self.type, dtype.ArrayType):
            value = self.type.decode( bytes[self.slice()], index, raw )
        else:
            value = self.type.decode( bytes[self.slice()], raw )


        # Apply bit mask if needed
        if self.mask is not None:
            value &= self.mask

        if self.shift > 0:
            value >>= self.shift

        if not raw and self.enum is not None:
            value = self.enum.get(value, value)

        return value


    def encode(self, value):
        """Encodes the given value according to this FieldDefinition."""
        if type(value) == str and self.enum and value in self.enum:
            value = self.enum[value]

        if type(value) == int:
            if self.shift > 0:
                value <<= self.shift
            if self.mask is not None:
                value &= self.mask

        return self.type.encode(value) if self.type else bytearray()


    def slice(self, offset=0):
        """Returns a Python slice object (e.g. for array indexing) indicating
        the start and stop byte position of this Telemetry field.  The
        start and stop positions may be translated by the optional
        byte offset.
        """
        if self.bytes is None:
            start = 0
            stop  = start + self.nbytes
        elif type(self.bytes) is int:
            start = self.bytes
            stop  = start + self.nbytes
        else:
            start = self.bytes[0]
            stop  = self.bytes[1] + 1

        return slice(start + offset, stop + offset)


    def validate(self, value, messages=None):
        """Returns True if the given field value is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        valid     = True
        primitive = value

        def log(msg):
            if messages is not None:
                messages.append(msg)

        if self.enum:
            if value not in self.enum.values():
                valid = False
                flds = (self.name, str(value))
                log("%s value '%s' not in allowed enumerated values." % flds)
            else:
                primitive = int(self.enum.keys()[self.enum.values().index(value)])

        if self.type:
            if self.type.validate(primitive, messages, self.name) is False:
                valid = False

        return valid



class Packet(object):
    """Packet
    """
    def __init__(self, defn, data=None):
        """Creates a new Packet based on the given Packet Definition and
        binary (raw) packet data.
        """
        object.__setattr__(self, '_defn', defn)

        if data is None:
            data = bytearray(self.nbytes)
        elif not isinstance(data, bytearray):
            data = bytearray(data)

        object.__setattr__(self, '_data', data)

        if defn.history:
            defn.history.add(self)

    def __repr__(self):
        return self._defn.__repr__()


    def __getattr__(self, fieldname):
        """Returns the value of the given packet field name."""
        return self._getattr(fieldname)


    def __setattr__(self, fieldname, value):
        """Sets the given packet field name to value."""
        self._assertField(fieldname)

        defn    = self._defn.fieldmap[fieldname]
        bytes   = defn.encode(value)
        indices = defn.slice()

        if defn.mask is not None:
            # If a mask is defined on the FieldDefinition (defn),
            # defn.encode() will return the encoded value
            # appropriately bit-shifted and masked.  This value, which
            # could span several bytes must now be integrated
            # byte-by-byte into the already existing data bytes of the
            # packet (self._data), taking care not to clobber any bits
            # outside the mask.  To accomplish this, for each byte at
            # byte position b:
            #
            #   1.  Bitwise-AND the existing value (data[b]) with the
            #       bitwise-COMPLEMENT of mask[b] to zero-out (clear)
            #       only the masked bits of the existing value, then
            #
            #   2.  Bitwise-OR with the the new byte value (bytes[b])
            #       to set the appropriate bits.

            data = self._data[indices]
            mask = bytearray(struct.pack(defn.type.format, defn.mask))

            for b in range( len(data) ):
                bytes[b] |= (data[b] & ~mask[b])

        self._data[indices] = bytes


    def _assertField(self, fieldname):
        """Raise AttributeError when Packet has no field with the given
        name."""
        if not self._hasattr(fieldname):
            values = self._defn.name, fieldname
            raise AttributeError("Packet '%s' has no field '%s'" % values)


    def _getattr (self, fieldname, raw=False, index=None):
        """Returns the value of the given packet field name.

        If raw is True, the field value is only decoded.  That is no
        enumeration substituions or DN to EU conversions are applied.
        """
        self._assertField(fieldname)
        value = None

        if fieldname == 'raw':
            value = createRawPacket(self)
        elif fieldname == 'history':
            value = self._defn.history
        else:
            defn = self._defn.fieldmap[fieldname]

            if isinstance(defn.type, dtype.ArrayType) and index is None:
                return createFieldList(self, defn, raw)

            if defn.when is None or defn.when.eval(self):
                if raw or (defn.dntoeu is None and defn.expr is None):
                    value = defn.decode(self._data, raw, index)
                elif defn.dntoeu is not None:
                    value = defn.dntoeu.eval(self)
                elif defn.expr is not None:
                    value = defn.expr.eval(self)

        return value


    def _hasattr(self, fieldname):
        """Returns True if this packet contains fieldname, False otherwise."""
        special = 'history', 'raw'
        return fieldname in special or fieldname in self._defn.fieldmap


    @property
    def nbytes(self):
        """The size of this packet in bytes."""
        return self._defn.nbytes


    @property
    def words(self):
        """Packet data as a wordarray."""
        return wordarray(self._data)


    def toJSON(self):
        return { name: getattr(self, name) for name in self._defn.fieldmap }


    def validate(self, messages=None):
        """Returns True if the given Packet is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        return self._defn.validate(self, messages)



class PacketContext(object):
    """PacketContext

    A PacketContext provides a simple wrapper around a Packet so that
    field accesses of the form:

        packet.fieldname

    may also be specified as:

        packet[fieldname]

    This latter syntax allows a PacketContext to be used as a symbol
    table when evaluating PacketExpressions.
    """

    __slots__ = [ '_packet' ]


    def __init__(self, packet):
        """Creates a new PacketContext for the given Packet."""
        self._packet = packet


    def __getitem__(self, name):
        """Returns packet[name]"""
        result = None
        packet = self._packet

        if self._packet._hasattr(name):
            result = self._packet._getattr(name)
        else:
            msg    = "Packet '%s' has no field '%s'"
            values = self._packet._defn.name, name
            raise KeyError(msg % values)

        return result


class PacketDefinition(json.SlotSerializer, object):
    """PacketDefinition
    """
    NextUID   = 1
    __slots__ = [ 'ccsds', 'constants', 'desc', 'fields', 'fieldmap',
                  'functions', 'globals', 'history', 'name', 'uid' ]

    def __init__(self, *args, **kwargs):
        """Creates a new PacketDefinition."""
        for slot in PacketDefinition.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, slot, kwargs.get(name, None))

        if self.ccsds:
            import ccsds
            self.ccsds = ccsds.CcsdsDefinition(**self.ccsds)

        if self.fields is None:
            self.fields   = [ ]
            self.fieldmap = { }
        else:
            self.fields   = handle_includes(self.fields)
            self.fieldmap = { defn.name: defn for defn in self.fields }

        if self.history:
            self.history = PacketHistory(self, names=self.history)

        if self.ccsds:
            self.uid = self.ccsds.apid
        else:
            self.uid                  = PacketDefinition.NextUID
            PacketDefinition.NextUID += 1

        self._update_globals()
        self._update_bytes(self.fields)


    def __repr__(self):
        return util.toRepr(self)

    def __getstate__(self):
        return {
            name: getattr(self, name)
            for name in PacketDefinition.__slots__ if name != 'globals'
        }

    def __setstate__(self, state):
        for s in PacketDefinition.__slots__:
            setattr(self, s, state.get(s, None))
        self._update_globals()


    def _update_bytes(self, defns, start=0):
        """Updates the 'bytes' field in all FieldDefinition.

        Any FieldDefinition.bytes which is undefined (None) or '@prev'
        will have its bytes field computed based on its data type size
        and where the previous FieldDefinition ended (or the start
        parameter in the case of very first FieldDefinition).  If
        bytes is set to '@prev', this has the effect of *starting* the
        FieldDefinition at the same place as the *previous*
        FieldDefinition.  This reads well in YAML, e.g.:

          bytes: '@prev'

        Returns the end of the very last FieldDefinition in Python
        slice notation, i.e. [start, stop).  This would correspond to
        the *start* of the next FieldDefinition, if it existed.
        """

        pos = slice(start, start)
        for fd in defns:
            if fd.bytes == '@prev' or fd.bytes is None:
                if fd.bytes == '@prev':
                    fd.bytes = None
                    pos      = fd.slice(pos.start)
                elif fd.bytes is None:
                    pos      = fd.slice(pos.stop)
                if pos.start == pos.stop - 1:
                    fd.bytes = pos.start
                else:
                    fd.bytes = [ pos.start, pos.stop - 1 ]
            pos = fd.slice()
        return pos.stop


    def _update_globals(self):
        if self.globals is None:
            self.globals = { }
            exec('from math import *', self.globals)
            util.__load_functions__(self.globals)

        if self.constants:
            self.globals.update(self.constants)

        if self.functions:
            for signature, body in self.functions.items():
                fn = createPacketFunction(signature, body, self.globals)
                self.globals[fn.name] = fn._func

        if self.history:
            self.globals['history'] = self.history


    @property
    def nbytes(self):
        """The number of bytes for this telemetry packet"""
        max_byte = -1

        for defn in self.fields:
            byte = defn.bytes if type(defn.bytes) is int else max(defn.bytes)
            max_byte = max(max_byte, byte)

        return max_byte + 1


    def validate(self, pkt, messages=None):
        """Returns True if the given Packet is valid, False otherwise.
        Validation error messages are appended to an optional messages
        array.
        """
        valid = True

        for f in self.fields:
            try:
                value = getattr(pkt, f.name)
            except AttributeError:
                valid = False
                if messages is not None:
                    msg = "Telemetry field mismatch for packet '%s'.  "
                    msg += "Unable to retrieve value for %s in Packet."
                    values = self.name, f.name
                    messages.append(msg % values)
                break

            if f.validate(value, messages) is False:
                valid = False

        return valid


    def toJSON(self):
        slots = ['name', 'desc', 'constants', 'functions', 'history', 'uid']

        if self.ccsds is not None:
            slots += 'ccsds'

        obj   = json.slotsToJSON(self, slots)
        obj['fields'] = { defn.name: defn.toJSON() for defn in self.fields }
        return obj



class PacketExpression(object):
    """PacketExpression

    A Packet Expression is a simple mathematical expression that can
    be evaluted in the context of a Packet.  Names in the formula
    refer to fields in the packet.

    Packet Expressions provide a convenient mechanism to express and
    perform Digital Number (DN) to Engineering Unit (EU) conversions.
    They can also be used to specify packet field guard conditions.
    For example, a packet field may only be interpreted as a
    particular housekeeping value when a corresponding mux field in
    the same packet is equal to some contsant value.

    """

    __slots__ = [ '_code', '_expr' ]


    def __init__(self, expr):
        """Creates a new PacketExpression from the given string expression."""
        self._code = compile(expr, '<string>', mode='eval')
        self._expr = expr


    def __reduce__(self):
        """Pickles and Unpickles PacketExpressions.

        Since Python code object cannot be Pickled, this method tells
        Python picklers to pickle this class as a string expression
        and unpickle by passing that string to the PacketExpression
        constructor.
        """
        return (PacketExpression, (self._expr, ))


    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self._expr)


    def __str__(self):
        return self._expr


    def eval(self, packet):
        """Returns the result of evaluating this PacketExpression in the
        context of the given Packet.
        """
        try:
            context = createPacketContext(packet)
            result  = eval(self._code, packet._defn.globals, context)
        except ZeroDivisionError:
            result = None

        return result


    def toJSON(self):
        return self._expr



class PacketFunction(object):
    """PacketFunction
    """

    __slots__ = [ '_args', '_expr', '_func', '_name', '_sig' ]

    def __init__(self, signature, expression, syms):
        """Creates a new PacketFunction from the given string signature and
        expression.
        """
        self._sig  = signature
        self._expr = expression

        lparen = signature.find('(')
        rparen = signature.find(')')

        if lparen == -1 or rparen == -1:
            msg = 'Function signature "%s" has no parentheses'
            raise SyntaxError(msg % signature)

        defn = 'def %s:\n' % signature

        if type(expression) is dict:
            for cond, subexpr in expression.items():
                defn += '    if (%s):\n' % self.__sanitize(cond)
                defn += '        return (%s)\n' % subexpr
        else:
            defn += '    return (%s)\n' % str(expression)


        args = signature[lparen + 1:rparen]

        exec(defn, syms)
        del syms['__builtins__']

        self._args = [ a.strip() for a in args.split(',') ]
        self._name = signature[:lparen].strip()
        self._func = syms[self._name]


    def __reduce__(self):
        """Pickles and Unpickles PacketFunctions.

        Since Python code object cannot be pickled, this method tells
        Python picklers to pickle this class as a string expression
        and unpickle by passing that string to the PacketFunction
        constructor.
        """
        return (PacketFunction, (self._sign, self._expr))


    def __repr__(self):
        s = '%s("%s", ' % (self.__class__.__name__, self._sig)

        if type(self._expr) is dict:
            s += '%s)' % repr(self._expr)
        else:
            s += '"%s")' % str(self._expr)

        return s


    def __str__(self):
        s = '%s:' % self._sig

        if type(self._expr) is dict:
            for cond, subexpr in self._expr.items():
                s += '\n    %s: %s' % (cond.encode('utf-8'), subexpr)
        else:
            s += ' %s' % str(self._expr)

        return s


    def __sanitize (self, cond):
        return str( cond.replace(u'\u2264', '<=').replace(u'\u2265', '>=') )


    def invoke(self, *args):
        """Returns the result of invoking this PacketFunction."""
        return self._func.__call__(*args)


    @property
    def arguments (self):
        return self._args


    @property
    def expression (self):
        return self._expr


    @property
    def name (self):
        return self._name


    @property
    def signature (self):
        return self._sig



class PacketHistory(object):
    """PacketHistory
    """

    __slots__ = [ '_defn', '_dict', '_names' ]

    def __init__(self, defn, names=None):
        if names is None and defn.history is not None:
            names = defn.history

        if names is None:
            names = [ ]

        self._defn  = defn
        self._names = names
        self._dict  = { name: 0 for name in names }


    def __contains__(self, fieldname):
        """Returns True if fieldname is in this PacketHistory."""
        return fieldname in self._names


    def __getattr__(self, fieldname):
        """Returns the value of the given packet field name."""
        self._assertField(fieldname)
        return self._dict.get(fieldname, None)


    def __getitem__(self, fieldname):
        """Returns packet.fieldname"""
        return self._dict.get(fieldname, None)


    def __getstate__(self):
        """Serialize state, avoiding __getattr__()."""
        return { s: getattr(self, s) for s in PacketHistory.__slots__ }


    def __setstate__(self, state):
        """Deserialize state, avoiding __getattr__()."""
        for s in PacketHistory.__slots__:
            setattr(self, s, state.get(s, None))


    def _assertField(self, name):
        """Raise AttributeError when PacketHistory has no field with the given
        name.
        """
        if name not in self._names:
            msg    = 'PacketHistory "%s" has no field "%s"'
            values = self._defn.name, name
            raise AttributeError(msg % values)

    def add(self, packet):
        """Add the given Packet to this PacketHistory."""
        for name in self._names:
            value = getattr(packet, name)
            if value is not None:
                self._dict[name] = value

    def toJSON(self):
        return self._names



class RawPacket(object):
    """RawPacket

    Wraps a packet such that:

        packet.raw.fieldname

    returns the value of fieldname as a raw value with no enumeration
    substitutions or DN to EU conversions applied.
    """

    __slots__ = [ '_packet' ]


    def __init__(self, packet):
        """Creates a new RawPacket based on the given Packet."""
        self._packet = packet


    def __getattr__(self, fieldname):
        """Returns the value of the given packet fieldname as a raw
        value with no DN to EU conversion applied.
        """
        return self._packet._getattr(fieldname, raw=True)



class TlmDict(dict):
    """TlmDict

    Tlm Dictionaries provide a Python dictionary (i.e. hashtable)
    interface mapping Packet names to Packet Definitions.
    """
    def __init__(self, *args, **kwargs):
        """Creates a new Telemetry Dictionary from the given telemetry
        dictionary filename or YAML string.
        """
        self.filename = None

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add(self, defn):
        """Adds the given Packet Definition to this Telemetry Dictionary."""
        if defn.name not in self:
            self[defn.name] = defn
        else:
            msg = "Duplicate packet name '%s'" % defn.name
            log.error(msg)
            raise util.YAMLError(msg)

    def create(self, name, data=None):
        """Creates a new packet with the given definition and raw data.
        """
        return createPacket(self[name], data) if name in self else None

    def load(self, content):
        """Loads Packet Definitions from the given YAML content into this
        Telemetry Dictionary.  Content may be either a filename
        containing YAML content or a YAML string.

        Load has no effect if this Command Dictionary was already
        instantiated with a filename or YAML content.
        """
        if self.filename is None:
            if os.path.isfile(content):
                self.filename = content
                stream        = open(self.filename, 'rb')
            else:
                stream        = content

            pkts = yaml.load(stream)
            pkts = handle_includes(pkts)
            for pkt in pkts:
                self.add(pkt)

            if type(stream) is file:
                stream.close()

    def toJSON(self):
        return { name: defn.toJSON() for name, defn in self.items() }



class TlmDictWriter(object):
    """TlmDictWriter

    Writes telemetry dictionary to a file in selected formats
    """
    def __init__(self, tlmdict=None):
        self.tlmdict = tlmdict or getDefaultDict()

    def writeToCSV(self, output_path=None):
        '''writeToCSV - write the telemetry dictionary to csv
        '''
        header = ['Name', 'First Byte', 'Last Byte', 'Bit Mask', 'Endian',
                  'Type', 'Description', 'Values']

        if output_path is None:
            output_path = ait.config._directory

        for pkt_name in self.tlmdict:
            filename = os.path.join(output_path, pkt_name + '.csv')

            with open(filename, 'wb') as output:
                csvwriter = csv.writer(output, quoting=csv.QUOTE_ALL)
                csvwriter.writerow(header)

                for fld in self.tlmdict[pkt_name].fields:
                    # Pre-process some fields

                    # Description
                    desc = fld.desc.replace('\n', ' ') if fld.desc is not None else ""

                    # Mask
                    mask = hex(fld.mask) if fld.mask is not None else ""

                    # Enumerations
                    enums = '\n'.join("%s: %s" % (k, fld.enum[k])
                            for k in fld.enum) if fld.enum is not None else ""

                    # Set row
                    row = [fld.name, fld.slice().start, fld.slice().stop,
                           mask, fld.type.endian, fld.type.name, desc, enums]

                    csvwriter.writerow(row)


def getDefaultDict(reload=False):
    return util.getDefaultDict(__name__, 'tlmdict', TlmDict, reload)


def getDefaultSchema():
    return pkg_resources.resource_filename('ait.core', 'data/tlm_schema.json')


def getDefaultDictFilename():
    return ait.config.tlmdict.filename


def handle_includes(defns):
    '''Recursive handling of includes for any input list of defns.
    The assumption here is that when an include is handled by the
    pyyaml reader, it adds them as a list, which is stands apart from the rest
    of the expected YAML definitions.
    '''
    newdefns = []
    for d in defns:
        if isinstance(d,list):
            newdefns.extend(handle_includes(d))
        else:
            newdefns.append(d)

    return newdefns

def YAMLCtor_PacketDefinition(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    return createPacketDefinition(**fields)


def YAMLCtor_FieldDefinition(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    return createFieldDefinition(**fields)


def YAMLCtor_include(loader, node):
    # Get the path out of the yaml file
    name = os.path.join(os.path.dirname(loader.name), node.value)
    data = None
    with open(name,'r') as f:
        data = yaml.load(f)
    return data

yaml.add_constructor('!include', YAMLCtor_include)
yaml.add_constructor('!Packet' , YAMLCtor_PacketDefinition)
yaml.add_constructor('!Field'  , YAMLCtor_FieldDefinition)

util.__init_extensions__(__name__, globals())
