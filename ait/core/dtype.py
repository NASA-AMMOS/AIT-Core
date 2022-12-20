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

from typing import Optional
from ait.core import util

"""AIT Primitive Data Types (PDT)

The ait.core.dtype module provides definitions and functions for
primitive data types used in the construction and manipulation of
OCO-3 commands and telemetry.  Originally, this module was named
ait.core.types, but types.py conflicts with Python's builtin module
of the same name, which causes all sorts of subtle import issues and
conflicts.

Supported PrimitiveType names (which may be passed to
ait.core.dtype.get()) are listed in ait.core.dtype.PrimitiveTypes.

The following code, shown via the interactive Python prompt,
demonstrates attributes and methods of the 'LSB_U16' PrimitiveType.
Several related statements are combined into a single line, forming
tuples, for succinctness:

    >>> from ait.core import dtype
    >>> t = dtype.get('LSB_U16')

    >>> t.name, t.endian, t.format, t.nbits, t.nbytes
    ('LSB_U16', 'LSB', '<H', 16, 2)

    >>> t.float, t.signed
    (False, False)

    >>> t.min, t.max
    (0, 65535)

    >>> bytes = t.encode(42)
    >>> ' '.join('0x%02x' % b for b in bytes)
    '0x2a 0x00'

    >>> t.decode(bytes)
    42

    >>> t.validate(42)
    True

    # Both the array of error messages and message prefixes are optional

    >>> messages = [ ]
    >>> t.validate(65536, messages, prefix='error:')
    False

    >>> t.validate(1e6, messages, prefix='error:')
    False

    >>> print("\\n".join(messages))
    error: value '65536' out of range [0, 65535].
    error: float '1e+06' cannot be represented as an integer.
"""

import datetime
import struct
import sys
import re

from typing import Dict, Any

from ait.core import cmd, dmc, log


# PrimitiveTypes
#
# Lists PrimitiveType names.  Passing these names to get() will return
# the corresponding PrimitiveType.
#
# (Populated below based on information in PrimitiveTypeFormats).
#
PrimitiveTypes = None


# PrimitiveTypeMap
#
# Maps typenames to PrimitiveType.  Use
# ait.core.dtype.get(typename).  (Populated below based on
# information in PrimitiveTypeFormats).
#
PrimitiveTypeMap: Dict[str, Any] = {}


# PrimitiveTypeFormats
#
# Maps typenames to their corresponding Python C struct format code.
# See:
#
#   https://docs.python.org/2/library/struct.html#format-characters
#
PrimitiveTypeFormats = {
    "I8": "b",
    "U8": "B",
    "LSB_I16": "<h",
    "MSB_I16": ">h",
    "LSB_U16": "<H",
    "MSB_U16": ">H",
    "LSB_I32": "<i",
    "MSB_I32": ">i",
    "LSB_U32": "<I",
    "MSB_U32": ">I",
    "LSB_I64": "<q",
    "MSB_I64": ">q",
    "LSB_U64": "<Q",
    "MSB_U64": ">Q",
    "LSB_F32": "<f",
    "MSB_F32": ">f",
    "LSB_D64": "<d",
    "MSB_D64": ">d",
}


class PrimitiveType:
    """PrimitiveType

    A PrimitiveType contains a number of fields that provide information
    on the details of a primitive type, including: name
    (e.g. "MSB_U32"), format (Python C struct format code), endianness
    ("MSB" or "LSB"), float, signed, nbits, nbytes, min, and max.

    PrimitiveTypes can validate() specific values and encode() and
    decode() binary representations.
    """

    def __init__(self, name):
        """PrimitiveType(name) -> PrimitiveType

        Creates a new PrimitiveType based on the given typename
        (e.g. 'MSB_U16' for a big endian, 16 bit short integer).
        """
        self._name = name
        self._format = PrimitiveTypeFormats.get(name, None)
        self._endian = None
        self._float = False
        self._min = None
        self._max = None
        self._signed = False
        self._string = False

        if self.name.startswith("LSB_") or self.name.startswith("MSB_"):
            self._endian = self.name[0:3]
            self._signed = self.name[4] != "U"
            self._float = self.name[4] == "F" or self.name[4] == "D"
            self._nbits = int(self.name[-2:])
        elif self.name.startswith("S"):
            self._format = self.name[1:] + "s"
            self._nbits = int(self.name[1:]) * 8
            self._string = True
        else:
            self._signed = self.name[0] != "U"
            self._nbits = int(self.name[-1:])

        self._nbytes = int(self._nbits / 8)

        if self.float:
            self._max = +sys.float_info.max
            self._min = -sys.float_info.max
        elif self.signed:
            self._max = 2 ** (self.nbits - 1)
            self._min = -1 * (self.max - 1)
        elif not self.string:
            self._max = 2 ** self.nbits - 1
            self._min = 0

    def __eq__(self, other):
        return isinstance(other, PrimitiveType) and self._name == other._name

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.name)

    @property
    def endian(self):
        """Endianness of this PrimitiveType, either 'MSB' or 'LSB'."""
        return self._endian

    @property
    def float(self):
        """Indicates whether or not this PrimitiveType is a float or double."""
        return self._float

    @property
    def format(self):
        """Python C struct format code for this PrimitiveType."""
        return self._format

    @property
    def name(self):
        """Name of this PrimitiveType (e.g. 'I8', 'MSB_U16', 'LSB_F32',
        etc.)."""
        return self._name

    @property
    def nbits(self):
        """Number of bits required to represent this PrimitiveType."""
        return self._nbits

    @property
    def nbytes(self):
        """Number of bytes required to represent this PrimitiveType."""
        return self._nbytes

    @property
    def min(self):
        """Minimum value for this PrimitiveType."""
        return self._min

    @property
    def max(self):
        """Maximum value for this PrimitiveType."""
        return self._max

    @property
    def signed(self):
        """Indicates whether or not this PrimitiveType is signed or unsigned."""
        return self._signed

    @property
    def string(self):
        """Indicates whether or not this PrimitiveType is a string."""
        return self._string

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        PrimitiveType definition.
        """
        if re.sub(r"\W+", "", self.format).lower() in ("b", "i", "l", "q"):
            fvalue = int(value)
        elif self._string:
            fvalue = value.encode()
        else:
            fvalue = value

        as_str = struct.pack(self.format, fvalue)
        return bytearray(as_str)

    def decode(self, bytestring, raw=False):
        """decode(bytearray, raw=False) -> value

        Decodes the given bytearray according to this PrimitiveType
        definition.

        NOTE: The parameter ``raw`` is present to adhere to the
        ``decode()`` inteface, but has no effect for PrimitiveType
        definitions.
        """
        return struct.unpack(self.format, memoryview(bytestring))[0]

    def toJSON(self):  # noqa
        return self.name

    def validate(self, value, messages=None, prefix=None):
        """validate(value[, messages[, prefix]]) -> True | False

        Validates the given value according to this PrimitiveType
        definition.  Validation error messages are appended to an optional
        messages array, each with the optional message prefix.
        """
        valid = False

        def log(msg):
            if messages is not None:
                if prefix is not None:
                    tok = msg.split()
                    msg = prefix + " " + tok[0].lower() + " " + " ".join(tok[1:])
                messages.append(msg)

        if self.string:
            if isinstance(value, str):
                valid = True
            else:
                log("Value '%s' is not a string type." % str(value))
        else:
            if isinstance(value, str):
                log("String '%s' cannot be represented as a number." % value)
            elif not isinstance(value, (int, float)):
                log("Value '%s' is not a primitive type." % str(value))
            elif isinstance(value, float) and not self.float:
                log("Float '%g' cannot be represented as an integer." % value)
            else:
                if value < self.min or value > self.max:
                    args = (str(value), self.min, self.max)
                    log("Value '%s' out of range [%d, %d]." % args)
                else:
                    valid = True

        return valid


#
# Populate the PrimitiveTypeMap based on the types in
# PrimitiveTypeFormats.
#
PrimitiveTypeMap.update((t, PrimitiveType(t)) for t in PrimitiveTypeFormats.keys())

PrimitiveTypes = sorted(PrimitiveTypeMap.keys())


class ArrayType(object):
    __slots__ = ["_nelems", "_type"]

    def __init__(self, elem_type, nelems):
        """Creates a new ArrayType of nelems, each of type elem_type."""
        if isinstance(elem_type, str):
            elem_type = get(elem_type)

        if not isinstance(nelems, int):
            raise TypeError("ArrayType(..., nelems) must be an integer")

        self._type = elem_type
        self._nelems = nelems

    def __eq__(self, other):
        """Returns True if two ArrayTypes are equivalent, False otherwise."""
        return (
            isinstance(other, ArrayType)
            and self.type == other.type
            and self.nelems == other.nelems
        )

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.name)

    def _assert_index(self, index):
        """Raise TypeError or IndexError if index is not an integer or out of
        range for the number of elements in this array, respectively.
        """
        if not isinstance(index, int):
            raise TypeError("list indices must be integers")
        if index < 0 or index >= self.nelems:
            raise IndexError("list index out of range")

    @property
    def name(self):
        """Name of this ArrayType."""
        return "%s[%d]" % (self.type.name, self.nelems)

    @property
    def nbits(self):
        """Number of bits required to represent this ArrayType."""
        return self.nelems * self.type.nbits

    @property
    def nbytes(self):
        """Number of bytes required to represent this ArrayType."""
        return self.nelems * self.type.nbytes

    @property
    def nelems(self):
        """Number of elements in this ArrayType."""
        return self._nelems

    @property
    def type(self):
        """Type of array elements."""
        return self._type

    def decode(self, bytes, index=None, raw=False):
        """decode(bytes[[, index], raw=False]) -> value1, ..., valueN

        Decodes the given sequence of bytes according to this Array's
        element type.

        If the optional `index` parameter is an integer or slice, then
        only the element(s) at the specified position(s) will be
        decoded and returned.
        """
        if index is None:
            index = slice(0, self.nelems)

        if isinstance(index, slice):
            step = 1 if index.step is None else index.step
            indices = range(index.start, index.stop, step)
            result = [self.decode_elem(bytes, n, raw) for n in indices]
        else:
            result = self.decode_elem(bytes, index, raw)

        return result

    def decode_elem(self, bytes, index, raw=False):
        """Decodes a single element at array[index] from a sequence bytes
        that contain data for the entire array.
        """
        self._assert_index(index)
        start = int(index * self.type.nbytes)
        stop = int(start + self.type.nbytes)

        if stop > len(bytes):
            msg = "Decoding %s[%d] requires %d bytes, "
            msg += "but the ArrayType.decode() method received only %d bytes."
            raise IndexError(msg % (self.type.name, index, stop, len(bytes)))

        return self.type.decode(bytes[start:stop], raw)

    def encode(self, *args):
        """encode(value1[, ...]) -> bytes

        Encodes the given values to a sequence of bytes according to this
        Array's underlying element type
        """
        if len(args) != self.nelems:
            msg = "ArrayType %s encode() requires %d values, but received %d."
            raise ValueError(msg % (self.name, self.nelems, len(args)))

        return bytearray().join(self.type.encode(arg) for arg in args)

    @staticmethod
    def parse(name):
        """parse(name) -> [typename | None, nelems | None]

        Parses an ArrayType name to return the element type name and
        number of elements, e.g.:

            >>> ArrayType.parse('MSB_U16[32]')
            ['MSB_U16', 32]

        If typename cannot be determined, None is returned.
        Similarly, if nelems is not an integer or less than one (1),
        None is returned.
        """
        parts = [None, None]
        start = name.find("[")

        if start != -1:
            stop = name.find("]", start)
            if stop != -1:
                try:
                    parts[0] = name[:start]
                    parts[1] = int(name[start + 1 : stop])
                    if parts[1] <= 0:
                        raise ValueError
                except ValueError:
                    msg = 'ArrayType specification: "%s" must have an '
                    msg += "integer greater than zero in square brackets."
                    raise ValueError(msg % name)

        return parts


class CmdType(PrimitiveType):
    """CmdType

    This type is used to take a two byte opcode and return the
    corresponding Command Definition (:class:`CmdDefn`).
    """

    BASEPDT = "MSB_U16"

    def __init__(self):
        super(CmdType, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = "CMD16"
        self._cmddict = None

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    @property
    def cmddict(self):
        """PrimitiveType base for the ComplexType"""
        if self._cmddict is None:
            self._cmddict = cmd.getDefaultDict()

        return self._cmddict

    @cmddict.setter
    def cmddict(self, value):
        """PrimitiveType base for the ComplexType"""
        self._cmddict = value

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        PrimitiveType definition.
        """
        opcode = self.cmddict[value].opcode
        return super(CmdType, self).encode(opcode)

    def decode(self, bytes, raw=False):
        """decode(bytearray, raw=False) -> value

        Decodes the given bytearray and returns the corresponding
        Command Definition (:class:`CmdDefn`) for the underlying
        'MSB_U16' command opcode.

        If the optional parameter ``raw`` is ``True``, the command
        opcode itself will be returned instead of the Command
        Definition (:class:`CmdDefn`).
        """
        opcode = super(CmdType, self).decode(bytes)
        result = None

        if raw:
            result = opcode
        elif opcode in self.cmddict.opcodes:
            result = self.cmddict.opcodes[opcode]
        else:
            raise ValueError("Unrecognized command opcode: %d" % opcode)

        return result


class EVRType(PrimitiveType):
    """EVRType

    This type is used to take a two byte Event Verification Record
    (EVR) code and return the corresponding EVR Definition
    (:class:`EVRDefn`).
    """

    BASEPDT = "MSB_U16"

    def __init__(self):
        super(EVRType, self).__init__(self.BASEPDT)

        self._pdt = self.name
        self._name = "EVR16"
        self._evrs = None

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    @property
    def evrs(self):
        """Getter EVRs dictionary"""
        if self._evrs is None:
            import ait.core.evr as evr

            self._evrs = evr.getDefaultDict()

        return self._evrs

    @evrs.setter
    def evrs(self, value):
        """Setter for EVRs dictionary"""
        self._evrs = value

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        Complex Type definition.
        """
        e = self.evrs.get(value, None)
        if not e:
            log.error(str(value) + " not found as EVR. Cannot encode.")
            return None
        else:
            return super(EVRType, self).encode(e.code)

    def decode(self, bytes, raw=False):
        """decode(bytearray, raw=False) -> value

        Decodes the given bytearray according the corresponding
        EVR Definition (:class:`EVRDefn`) for the underlying
        'MSB_U16' EVR code.

        If the optional parameter ``raw`` is ``True``, the EVR code
        itself will be returned instead of the EVR Definition
        (:class:`EVRDefn`).
        """
        code = super(EVRType, self).decode(bytes)
        result = None

        if raw:
            result = code
        elif code in self.evrs.codes:
            result = self.evrs.codes[code]
        else:
            result = code
            log.warn("Unrecognized EVR code: %d" % code)

        return result


class Time8Type(PrimitiveType):
    """Time8Type

    This 8-bit time type represents the fine time in the CCSDS
    secondary header. This time is calculated where the LSB of the
    octet is equal to 1/256 seconds (or 2^-8), approximately 4 msec.
    See SSP 41175-02H for more details on the CCSDS headers.
    """

    def __init__(self):
        super(Time8Type, self).__init__("U8")

        self._pdt = self.name
        self._name = "TIME8"

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        return super(Time8Type, self).encode(value * 256)

    def decode(self, bytes, raw=False):
        """decode(bytearray, raw=False) -> value

        Decodes the given bytearray and returns the number of
        (fractional) seconds.

        If the optional parameter ``raw`` is ``True``, the byte (U8)
        itself will be returned.

        """
        result = super(Time8Type, self).decode(bytes)

        if not raw:
            result /= 256.0

        return result


class Time32Type(PrimitiveType):
    """Time32Type

    This four byte time represents the elapsed time in seconds since
    the GPS epoch.
    """

    def __init__(self):
        super(Time32Type, self).__init__("MSB_U32")

        self._pdt = self.name
        self._name = "TIME32"

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        if not isinstance(value, datetime.datetime):
            raise TypeError("encode() argument must be a Python datetime")

        return super(Time32Type, self).encode(dmc.to_gps_seconds(value))

    def decode(self, bytes, raw=False):
        """decode(bytearray, raw=False) -> value

        Decodes the given bytearray containing the elapsed time in
        seconds since the GPS epoch and returns the corresponding
        Python :class:`datetime`.

        If the optional parameter ``raw`` is ``True``, the integral
        number of seconds will be returned instead.
        """
        sec = super(Time32Type, self).decode(bytes)
        return sec if raw else dmc.to_local_time(sec)


class Time40Type(PrimitiveType):
    """Time40Type

    This five byte time is made up of four bytes of seconds and one
    byte of (1 / 256) subseconds, representing the elapsed time since
    the GPS epoch.
    """

    def __init__(self):
        super(Time40Type, self).__init__("MSB_U32")

        self._pdt = self.name
        self._name = "TIME40"
        self._nbits = 40
        self._nbytes = 5

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        if not isinstance(value, datetime.datetime):
            raise TypeError("encode() argument must be a Python datetime")

        coarse = Time32Type().encode(value)
        fine = Time8Type().encode(value.microsecond / 1e6)

        return coarse + fine

    def decode(self, bytes, raw=False):
        """decode(bytearray, raw=False) -> value

        Decodes the given bytearray containing the elapsed time in
        seconds plus 1/256 subseconds since the GPS epoch returns the
        corresponding Python :class:`datetime`.

        If the optional parameter ``raw`` is ``True``, the number of
        seconds and subseconds will be returned as a floating-point
        number instead.
        """
        coarse = Time32Type().decode(bytes[:4], raw)
        fine = Time8Type().decode(bytes[4:])

        if not raw:
            fine = datetime.timedelta(microseconds=fine * 1e6)

        return coarse + fine


class Time64Type(PrimitiveType):
    """Time64Type

    This eight byte time is made up of four bytes of seconds and four
    bytes of nanoseconds, representing the elapsed time since the GPS
    epoch.
    """

    def __init__(self):
        super(Time64Type, self).__init__("MSB_U64")

        self._pdt = self.name
        self._name = "TIME64"

    @property
    def pdt(self):
        """PrimitiveType base for the ComplexType"""
        return self._pdt

    def encode(self, value):
        """encode(value) -> bytearray

        Encodes the given value to a bytearray according to this
        ComplexType definition.
        """
        if not isinstance(value, datetime.datetime):
            raise TypeError("encode() argument must be a Python datetime")

        coarse = Time32Type().encode(value)
        fine = get("MSB_U32").encode(value.microsecond * 1e3)

        return coarse + fine

    def decode(self, bytes, raw=False):
        """decode(bytearray, False) -> value

        Decodes the given bytearray containing the elapsed time in
        seconds plus nanoseconds since the GPS epoch and and returns
        the corresponding Python :class:`datetime`.  NOTE: The Python
        :class:`datetime` class has only microsecond resolution.

        If the optional parameter ``raw`` is ``True``, the number of
        seconds and nanoseconds will be returned as a floating-point
        number instead.
        """
        coarse = Time32Type().decode(bytes[:4], raw)
        fine = get("MSB_U32").decode(bytes[4:])

        if raw:
            fine /= 1e9
        else:
            fine = datetime.timedelta(microseconds=fine / 1e3)

        return coarse + fine


# ComplexTypeMap
#
# Maps typenames to Complex Types.  Use ait.core.dtype.get(typename).
#
ComplexTypeMap = {
    "CMD16": CmdType(),
    "EVR16": EVRType(),
    "TIME8": Time8Type(),
    "TIME32": Time32Type(),
    "TIME40": Time40Type(),
    "TIME64": Time64Type(),
}


class CustomTypes:
    '''Pseudo-ABC for users to inject custom types into AIT

    CustomTypes is the vector through which users can inject custom types that
    they create into the toolkit. `dtype.get` is used throughout AIT to fetch
    the appropriate class for a given data type. Users that want to create a
    custom type should inherit from CustomTypes, implement `get()` so their
    types can be exposed, and configure AIT's extensions to use their class.

    Custom classes must inherit from PrimitiveType. For examples of "custom"
    types look at the implementation of the `ComplexTypeMap` classes. All of
    these build on top of PrimitiveType in some way.
    '''

    def get(self, typename: str) -> Optional[PrimitiveType]:
        '''Retrieve an instance of a type's class given its name

        Maps a class name to an instance of its respective class. Should
        return None if no match is found.
        '''
        return None


def get_pdt(typename):
    """Returns the PrimitiveType for typename or None."""
    if typename not in PrimitiveTypeMap and typename.startswith("S"):
        PrimitiveTypeMap[typename] = PrimitiveType(typename)

    return PrimitiveTypeMap.get(typename, None)


def get_cdt(typename):
    """Returns the ComplexType for typename or None."""
    return ComplexTypeMap.get(typename, None)


def get(typename):
    """Returns the type for typename or None.

    `get()` checks primitive types, then complex types, and finally custom
    user defined types (via CustomTypes extension) for the typename.
    """
    dt = get_pdt(typename) or get_cdt(typename) or USER_DEFN_TYPES.get(typename)

    if dt is None:
        pdt, nelems = ArrayType.parse(typename)
        if pdt and nelems:
            dt = ArrayType(pdt, nelems)

    return dt


util.__init_extensions__(__name__, globals())

# Note, this must be defined after the `util.__init_extensions__` call in order
# for the magical createXXX function to exist.
USER_DEFN_TYPES = createCustomTypes()  # type: ignore[name-defined] # noqa: F821
