# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2021, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.
import datetime
import hashlib
import io
import os
import pickle
import yaml

import ait

from ait.core import dmc
from ait.core import dtype
from ait.core import log
from ait.core import util


class FSWColDefn(object):
    """FSWColDefn - Argument Definition

    Argument Definitions encapsulate all information required to define
    a single column.
    """

    def __init__(self, *args, **kwargs):
        """Creates a new Column Definition."""
        self.name = kwargs.get("name", None)
        self.type = kwargs.get("type", None)
        self.units = kwargs.get("units", None)
        self.enum = kwargs.get("enum", None)

        self._enum_rev = None
        if self.enum is not None:
            self._enum_rev = dict((v, k) for k, v in self.enum.items())

            if len(self.enum) != len(self._enum_rev):
                msg = (
                    f"Table enumeration mappings are not one-to-one for '{self.name}'. "
                    "This may result in expected or incorrect results when encoding or "
                    "decoding. Remove enumerations from this column or proceed with caution"
                )
                log.error(msg)

    def __repr__(self):
        return util.toRepr(self)

    def decode(self, in_stream, raw=False):
        """Decode a column's value according to its data type

        Read bytes equal to this column's data type from the input stream
        and decode it into a value per that data type's definition.

        Arguments:
            in_stream: A file-like object from which to read data.

            raw: Flag denoting whether raw values or enumerate values
                (if present for this column) should be returned.

        Raises:
            EOFError: If the number of bytes read from the input stream
                is less than the length of the data type.
        """
        val = None
        dt = dtype.get(self.type)

        if dt is not None:
            data = in_stream.read(dt.nbytes)

            if len(data) != dt.nbytes:
                raise EOFError

            if (
                isinstance(dt, dtype.Time64Type)
                or isinstance(dt, dtype.Time40Type)
                or isinstance(dt, dtype.Time32Type)
            ):
                val = dt.decode(data).strftime(dmc.RFC3339_Format)
            else:
                val = dt.decode(data, raw=True)

        if self.enum and not raw:
            val = self.enum.get(val, val)

        return val

    def encode(self, value):
        """Encode a columns value according to its data type

        Arguments:
            value: The value to encode provided as either a string or
                the appropriate type for the column's data type.
        """
        dt = dtype.get(self.type)

        if self._enum_rev is not None:
            value = self._enum_rev.get(value, value)

        value = self._parse_column_value_from_string(value)

        # For some reason ArrayType.encode expects to receive the values
        # for encoding in *args instead of, you know, an iterable ...
        if isinstance(dt, dtype.ArrayType):
            # `value` needs to be an unpackable iterable or this is going
            # to explode. More than likely this'll be a bytearray.
            return dt.encode(*value)
        else:
            return dt.encode(value)

    def _parse_column_value_from_string(self, value):
        """Parse strings into an appropriate type for a given table column

        Attempt to cast a string value into the appropriate data type for a
        column to use during encoding. If the column's type is a "Primitive"
        type as defined in ait.core.dtype then we simple cast to float or int
        depending on the definition. ArrayType values must be passed as a
        string which can be encoded into a binary string. All other AIT
        data types are not supported in the table module.

        Arguments:
            value: The string from which to extract an appropriate data type
                value for future processing. If this is not a string it is
                returned without modification.
        """
        if not isinstance(value, str):
            return value

        col_defn = dtype.get(self.type)

        if isinstance(col_defn, dtype.ArrayType):
            # Value is expected to be a string which can be encoded to a
            # binary string for use by a bytes-like object.
            #
            # E.g., for a type of U8[2] the following is valid:
            #     value = '\x01\x02'
            return bytearray(value.encode("ascii"))
        elif (
            isinstance(col_defn, dtype.Time64Type)
            or isinstance(col_defn, dtype.Time40Type)
            or isinstance(col_defn, dtype.Time32Type)
        ):
            return datetime.datetime.strptime(value, dmc.RFC3339_Format)
        else:
            if col_defn.float:
                return float(value)
            else:
                return int(value, base=0)


class FSWTab(object):
    """Table object that contains column definitions"""

    def __init__(self, defn, *args):
        """Creates a new FSWTab based on the given definition arguments."""
        self.defn = defn
        self.args = args

    def __repr__(self):
        return self.defn.name + " " + " ".join([str(a) for a in self.args])

    @property
    def coldefns(self):
        """The table column definitions."""
        return self.defn.coldefns

    @property
    def fswheaderdefns(self):
        """The table fsw header definitions."""
        return self.defn.fswheaderdefns


def hash_file(filename):
    """Calculate SHA-1 hash of the passed file"""

    # make a hash object
    h = hashlib.sha1()

    # open file for reading in binary mode
    with open(filename, "rb") as file:

        # loop till the end of the file
        chunk = 0
        while chunk != b"":
            # read only 1024 bytes at a time
            chunk = file.read(1024)
            h.update(chunk)

    # return the hex representation of digest
    return h.hexdigest()


class FSWTabDefn(object):
    """Table Definition

    FSW Table Definitions encapsulate all information required to define a
    single column.  This includes the column name, its opcode,
    subsystem, description and a list of argument definitions.  Name and
    opcode are required.  All others are optional.
    """

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get("name", None)
        self.delimiter = kwargs.get("delimiter", None)
        self.size = kwargs.get("size", None)
        self.uptype = kwargs.get("uptype", None)
        self.fswheaderdefns = kwargs.get("fswheaderdefns", None)
        self.coldefns = kwargs.get("coldefns", None)

        if self.fswheaderdefns is None:
            self.fswheaderdefns = []

        if self.coldefns is None:
            self.coldefns = []

    def __repr__(self):
        return util.toRepr(self)

    def decode(self, **kwargs):
        """Decode table data according to the current table definition

        Decode table data (provided via either an input file or binary blob)
        given the current FSWTabDefn format. The decoded table data will be
        returned as a list of lists, each containing an individual row's
        field data. The first row of the returned data is the header's
        values if applicable for this table definition.

        Keyword Arguments:
            file_in (open file stream): A file stream from which to read
                the table data for decoding.

            bin_in (bytes-like object): An encoded binary table data.

            raw (boolean): Flag indicating whether columns with enumerations
                should return a raw value (True) or an enumerated value
                (False) when the option exists. (default: False)
        """
        # Setup the "iterator" from which to read input data. Input data is
        # passed as either an open file stream or a binary blob.
        in_stream = None
        if "file_in" in kwargs:
            in_stream = kwargs["file_in"]
        elif "bin_in" in kwargs:
            in_stream = io.BytesIO(kwargs["bin_in"])

        if in_stream is None:
            msg = "No valid input source provided to table.decode."
            log.error(msg)
            raise TypeError(msg)

        raw = kwargs.get("raw", False)

        table = []

        # Extract header column names and values if applicable.
        if len(self.fswheaderdefns) > 0:
            table.append(
                [col.decode(in_stream, raw=raw) for col in self.fswheaderdefns]
            )

        # Decode rows from the remaining data
        while True:
            row = self._decode_table_row(in_stream, raw=raw)

            if row is None:
                break

            table.append(row)

        return table

    def encode(self, **kwargs):
        """Encode table data according to the current table definition

        Encode table data (provided via either an input file or list of table rows)
        given the current FSWTabDefn format. Header data to be encoded can be
        included as the first non-comment row in the input stream or as a separate
        list of column values under the `hdr_vals` kwarg. Lines starting with a '#'
        are considered comments and discarded.

        Rows of table data (header or otherwise) should use the given table
        definitions delimiter to separate entries. Extra whitespace around entries
        is stripped whenever possible.

        Keyword Arguments:
            file_in (open file stream): A file stream from which to read
                the table data for encoding.

            text_in (list): A list of row strings to use when encoding
                the table data.

            hdr_vals (list): An optional list of values to use when encoding
                the header row. If values are passed here then no header values
                should be present in the input data source. Overlap here will
                result in unexpected behavior.

        """
        # Setup the iterator from which to read input data. Input data is
        # passed as either an open file stream or a list of table "lines".
        in_iter = None
        if "file_in" in kwargs:
            in_iter = kwargs["file_in"]
        elif "text_in" in kwargs:
            in_iter = kwargs["text_in"]

        if in_iter is None:
            msg = "No valid input source provided to table.encode."
            log.error(msg)
            raise TypeError(msg)

        in_iter = iter(in_iter)
        encoded = bytearray()

        # Skip header-encoding for tables without a header definition
        if len(self.fswheaderdefns) > 0:
            # Read / locate header values either from kwargs or by reading the input file.
            # hdr_vals = [i.strip() for i in kwargs['hdr_vals']] if 'hdr_vals' in kwargs else None
            hdr_vals = kwargs.get("hdr_vals", None)

            # If no header values are provided we read them from the input stream
            while hdr_vals is None:
                r = next(in_iter).strip()
                if r.startswith("#") or r == "":
                    continue

                hdr_vals = r.split(self.delimiter)

            # Sanity check that we at least got the correct number of header values
            if len(hdr_vals) != len(self.fswheaderdefns):
                msg = (
                    "Incorrect number of header fields provided. Received "
                    f"{len(hdr_vals)} instead of expected {len(self.fswheaderdefns)}"
                )
                log.error(msg)
                raise ValueError(msg)

            # Encode the header values
            for defn, val in zip(self.fswheaderdefns, hdr_vals):
                encoded += defn.encode(val)

        # Encode each row of the table
        for row in in_iter:
            row = row.strip()
            if row.startswith("#") or row == "":
                continue

            elems = [i.strip() for i in row.split(self.delimiter)]
            for defn, val in zip(self.coldefns, elems):
                encoded += defn.encode(val)

        return encoded

    def _decode_table_row(self, in_stream, raw=False):
        """Decode a table row from an input stream

        Attempt to read and decode a row of data from an input stream. If this
        runs out of a data on a "seemingly invalid column" (e.g., not the first)
        then raise an exception. Similarly, if any column decodes into None, this
        will raise an exception.

        Arguments:
            in_stream: A file-like object from which to read data.

            raw: Boolean indicating whether raw or enumerated values should be returned.
                (default: False which returns enumerated values if possible)

        Raises:
            ValueError: When an EOFError is encountered while decoding any column
                but the first or if any column decode returns None.
        """

        row = []
        for i, col in enumerate(self.coldefns):
            try:
                row.append(col.decode(in_stream, raw=raw))
            except EOFError:
                if i == 0:
                    log.debug("Table processing stopped when EOF reached")
                    return None
                else:
                    msg = (
                        "Malformed table data provided for decoding. End of file "
                        f"reached when processing table column {i} {col.name}"
                    )
                    log.info(msg)
                    raise ValueError(msg)

            if row[-1] is None:
                msg = f"Failed to decode table column {col.name}"
                log.error(msg)
                raise ValueError(msg)

        return row


class FSWTabDict(dict):
    """Table dictionary object

    Table Dictionaries provide a Python dictionary (i.e. hashtable)
    interface mapping Tables names to Column Definitions.
    """

    def __init__(self, *args, **kwargs):
        """Creates a new Table Dictionary from the given dictionary filename."""
        self.filename = None
        self.colnames = {}

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add(self, defn):
        """Adds the given Table Definition to this Table Dictionary."""
        self[defn.name] = defn
        self.colnames[defn.name] = defn

    def create(self, name, *args):
        """Creates a new table with the given arguments."""
        tab = None
        defn = self.get(name, None)
        if defn:
            tab = FSWTab(defn, *args)
        return tab

    def load(self, filename):
        """Loads Table Definitions from the given YAML file into this
        Table Dictionary.
        """
        if self.filename is None:
            self.filename = filename

        stream = open(self.filename, "rb")
        for doc in yaml.load_all(stream, Loader=yaml.Loader):
            for table in doc:
                self.add(table)
        stream.close()


class FSWTabDictCache(object):
    def __init__(self, filename=None):
        if filename is None:
            filename = ait.config.get("table.filename")

        self.filename = filename
        self.cachename = os.path.splitext(filename)[0] + ".pkl"
        self.fswtabdict = None

    @property
    def dirty(self):
        """True if the pickle cache needs to be regenerated, False to use current pickle binary"""
        return util.check_yaml_timestamps(self.filename, self.cachename)

    def load(self):
        if self.fswtabdict is None:
            if self.dirty:
                self.fswtabdict = FSWTabDict(self.filename)
                util.update_cache(self.filename, self.cachename, self.fswtabdict)
                log.info(f'Loaded new pickle file: {self.cachename}')
            else:
                with open(self.cachename, "rb") as stream:
                    self.fswtabdict = pickle.load(stream)
                log.info(f'Current pickle file loaded: {self.cachename.split("/")[-1]}')

        return self.fswtabdict


_DefaultFSWTabDictCache = FSWTabDictCache()


def getDefaultFSWTabDict():  # noqa: N802
    fswtabdict = None
    filename = None
    try:
        filename = _DefaultFSWTabDictCache.filename
        fswtabdict = _DefaultFSWTabDictCache.load()
    except IOError as e:
        msg = "Could not load default table dictionary '%s': %s'"
        log.error(msg, filename, str(e))

    return fswtabdict


def getDefaultDict():  # noqa: N802
    return getDefaultFSWTabDict()


def YAMLCtor_FSWColDefn(loader, node):  # noqa: N802
    fields = loader.construct_mapping(node, deep=True)
    return FSWColDefn(**fields)


def YAMLCtor_FSWTabDefn(loader, node):  # noqa: N802
    fields = loader.construct_mapping(node, deep=True)
    fields["fswheaderdefns"] = fields.pop("header", None)
    fields["coldefns"] = fields.pop("columns", None)
    return FSWTabDefn(**fields)


def encode_to_file(tbl_type, in_path, out_path):
    tbldict = getDefaultDict()
    try:
        defn = tbldict[tbl_type]
    except KeyError:
        msg = f"Table type {tbl_type} not found in table dictionary."
        log.error(f"table.encode_to_file failed: {msg}")
        raise ValueError(msg)

    with open(in_path, "r") as in_file:
        encoded = defn.encode(file_in=in_file)

    with open(out_path, "wb") as out_file:
        out_file.write(encoded)


def decode_to_file(tbl_type, in_path, out_path):
    tbldict = getDefaultDict()
    try:
        defn = tbldict[tbl_type]
    except KeyError:
        msg = f"Table type {tbl_type} not found in table dictionary."
        log.error(f"table.encode_to_file failed: {msg}")
        raise ValueError(msg)

    with open(in_path, "rb") as in_file:
        decoded = defn.decode(file_in=in_file)

    with open(out_path, "w") as out_file:
        for line in decoded:
            print(defn.delimiter.join(map(str, line)), file=out_file)


yaml.add_constructor("!FSWTable", YAMLCtor_FSWTabDefn)
yaml.add_constructor("!FSWColumn", YAMLCtor_FSWColDefn)
