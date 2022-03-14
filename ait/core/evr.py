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
AIT Event Record (EVR) Reader

The ait.core.evr module is used to read the EVRs from a YAML file.
"""

import os
import pkg_resources
import re
import yaml

import ait.core
from ait.core import dtype, json, log, util


class EVRDict(dict):
    def __init__(self, *args, **kwargs):
        self.filename = None
        self.codes = {}

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add(self, defn):
        if defn.name not in self and defn.code not in self.codes:
            self[defn.name] = defn
            self.codes[defn.code] = defn
        else:
            msg = "EVRDict: Duplicate EVR name/code {}".format(defn)
            log.error(msg)
            raise util.YAMLError(msg)

    def load(self, content):
        if self.filename:
            log.warn("EVRDict: Skipping load() attempt after previous initialization")
            return

        if os.path.isfile(content):
            self.filename = content
            stream = open(self.filename, "rb")
        else:
            stream = content

        try:
            evrs = yaml.load(stream, Loader=yaml.Loader)
        except IOError as e:
            msg = "Could not load EVR YAML '{}': '{}'".format(stream, str(e))
            log.error(msg)
            return

        for evr in evrs:
            self.add(evr)

    def toJSON(self):  # noqa
        return {code: defn.toJSON() for code, defn in self.items()}


def getDefaultSchema():  # noqa
    return pkg_resources.resource_filename("ait.core", "data/evr_schema.json")


def getDefaultDict(reload=False):  # noqa
    return util.getDefaultDict(__name__, "evrdict", EVRDict, reload)


def getDefaultEVRs():  # noqa
    return getDefaultDict()


def getDefaultDictFilename():  # noqa
    return ait.config.evrdict.filename


class EVRDefn(json.SlotSerializer, object):
    """"""

    __slots__ = ["name", "code", "desc", "_message"]

    def __init__(self, *args, **kwargs):
        """Creates a new EVR Definition."""
        for slot in EVRDefn.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))

    def __repr__(self):
        return util.toRepr(self)

    def format_message(self, evr_hist_data):
        """Format EVR message with EVR data

        Given a byte array of EVR data, format the EVR's message attribute
        printf format strings and split the byte array into appropriately
        sized chunks. Supports most format strings containing length and type
        fields.

        Args:
            evr_hist_data: A bytearray of EVR data. Bytes are expected to be in
             MSB ordering.

            Example formatting::

                # This is the character '!', string 'Foo', and int '4279317316'
                bytearray([0x21, 0x46, 0x6f, 0x6f, 0x00, 0xff, 0x11, 0x33, 0x44])

        Returns:
            The EVR's message string formatted with the EVR data or the
            unformatted EVR message string if there are no valid format
            strings present in it.

        Raises:
            ValueError: When the bytearray cannot be fully processed with the
                specified format strings. This is usually a result of the
                expected data length and the byte array length not matching.
        """
        size_formatter_info = {
            "s": -1,
            "c": 1,
            "i": 4,
            "d": 4,
            "u": 4,
            "x": 4,
            "hh": 1,
            "h": 2,
            "l": 4,
            "ll": 8,
            "f": 8,
            "g": 8,
            "e": 8,
        }
        type_formatter_info = {
            "c": "U{}",
            "i": "MSB_I{}",
            "d": "MSB_I{}",
            "u": "MSB_U{}",
            "f": "MSB_D{}",
            "e": "MSB_D{}",
            "g": "MSB_D{}",
            "x": "MSB_U{}",
        }

        formatters = re.findall(r"%(?:\d+\$)?([cdieEfgGosuxXhlL]+)", self._message)

        cur_byte_index = 0
        data_chunks = []

        for f in formatters:
            # If the format string we found is > 1 character we know that a length
            # field is included and we need to adjust our sizing accordingly.
            f_size_char = f_type = f[-1]
            if len(f) > 1:
                f_size_char = f[:-1]

            fsize = size_formatter_info[f_size_char.lower()]

            try:
                if f_type != "s":
                    end_index = cur_byte_index + fsize
                    fstr = type_formatter_info[f_type.lower()].format(fsize * 8)

                    # Type formatting can give us incorrect format strings when
                    # a size formatter promotes a smaller data type. For instnace,
                    # 'hhu' says we'll promote a char (1 byte) to an unsigned
                    # int for display. Here, the type format string would be
                    # incorrectly set to 'MSB_U8' if we didn't correct.
                    if fsize == 1 and "MSB_" in fstr:
                        fstr = fstr[4:]

                    d = dtype.PrimitiveType(fstr).decode(
                        evr_hist_data[cur_byte_index:end_index]
                    )

                # Some formatters have an undefined data size (such as strings)
                # and require additional processing to determine the length of
                # the data and decode data.
                else:
                    end_index = evr_hist_data.find(0x00, cur_byte_index)
                    d = str(evr_hist_data[cur_byte_index:end_index], "utf-8")

                data_chunks.append(d)
            # TODO: Make this not suck
            except Exception:
                msg = "Unable to format EVR Message with data {}".format(evr_hist_data)
                log.error(msg)
                raise ValueError(msg)

            cur_byte_index = end_index

            # If we were formatting a string we need to add another index offset
            # to exclude the null terminator.
            if f == "s":
                cur_byte_index += 1

        # Format and return the EVR message if formatters were present, otherwise
        # just return the EVR message as is.
        if len(formatters) == 0:
            return self._message
        else:
            # Python format strings cannot handle size formatter information. So something
            # such as %llu needs to be adjusted to be a valid identifier in python by
            # removing the size formatter.
            msg = self._message
            for f in formatters:
                if len(f) > 1:
                    msg = msg.replace("%{}".format(f), "%{}".format(f[-1]))

            return msg % tuple(data_chunks)

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value


def YAMLCtor_EVRDefn(loader, node):  # noqa
    fields = loader.construct_mapping(node, deep=True)
    fields["argdefns"] = fields.pop("arguments", None)
    return createEVRDefn(**fields)  # noqa


yaml.add_constructor("!EVR", YAMLCtor_EVRDefn)

util.__init_extensions__(__name__, globals())
