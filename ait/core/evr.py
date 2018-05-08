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

import binascii
import os
import pkg_resources
import re
import yaml

import ait
from ait.core import json, log, util


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
            log.warn('EVRDict: Skipping load() attempt after previous initialization')
            return

        if os.path.isfile(content):
            self.filename = content
            stream = open(self.filename, 'rb')
        else:
            stream = content

        try:
            evrs = yaml.load(stream)
        except IOError, e:
            msg = "Could not load EVR YAML '{}': '{}'".format(stream, str(e))
            log.error(msg)
            return

        for e in evrs:
            self.add(e)

    def toJSON(self):
        return {code: defn.toJSON() for code, defn in self.items()}


def getDefaultSchema():
    return pkg_resources.resource_filename('ait.core', 'data/evr_schema.json')


def getDefaultDict(reload=False):
    return util.getDefaultDict(__name__, 'evrdict', EVRDict, reload)


def getDefaultEVRs():
    return getDefaultDict()


def getDefaultDictFilename():
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
        ''' Format EVR message with EVR data

        Given a byte array of EVR data, format the EVR's message attribute
        printf format strings and split the byte array into appropriately
        sized chunks.

        Args:
            evr_hist_data: A bytearray of EVR data.

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
        '''
        formatter_info = {
            's': (-1, str),
            'c': (1, str),
            'i': (4, lambda h: int(binascii.hexlify(h), 16)),
            'd': (4, lambda h: int(binascii.hexlify(h), 16)),
            'u': (4, lambda h: int(binascii.hexlify(h), 16)),
            'f': (4, lambda h: float(binascii.hexlify(h), 16)),
            'e': (4, lambda h: float(binascii.hexlify(h), 16)),
            'g': (4, lambda h: float(binascii.hexlify(h), 16)),
        }
        formatters = re.findall("%(?:\d+\$)?([cdifosuxXhlL]+)", self._message)

        cur_byte_index = 0
        data_chunks = []

        for f in formatters:
            format_size, format_func = formatter_info[f]

            try:
                # Normal data chunking is the current byte index + the size
                # of the relevant data type for the formatter
                if format_size > 0:
                    end_index = cur_byte_index + format_size

                # Some formatters have an undefined data size (such as strings)
                # and require additional processing to determine the length of
                # the data.
                else:
                    if f == 's':
                        end_index = str(evr_hist_data).index('\x00', cur_byte_index)
                    else:
                        end_index = format_size

                data_chunks.append(format_func(evr_hist_data[cur_byte_index:end_index]))
            except:
                msg = "Unable to format EVR Message with data {}".format(evr_hist_data)
                ait.core.log.error(msg)
                raise ValueError(msg)

            cur_byte_index = end_index

            # If we were formatting a string we need to add another index offset
            # to exclude the null terminator.
            if f == 's':
                cur_byte_index += 1

        # Format and return the EVR message if formatters were present, otherwise
        # just return the EVR message as is.
        if len(formatters) == 0:
            return self._message
        else:
            return self._message % tuple(data_chunks)

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

def YAMLCtor_EVRDefn(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    fields['argdefns'] = fields.pop('arguments', None)
    return createEVRDefn(**fields)

yaml.add_constructor('!EVR' , YAMLCtor_EVRDefn)

util.__init_extensions__(__name__, globals())
