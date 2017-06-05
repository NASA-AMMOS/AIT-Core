# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Event Record (EVR) Reader

The bliss.core.evr module is used to read the EVRs from a YAML file.

Also includes deprecated EVRParser class for parsing the EVR
information from the FSW EVR classes.

"""

import binascii
import os
import pkg_resources
import re
import yaml

import bliss
from bliss.core import json, log, util


class EVRReader(object):
    """EVRReader

    Reads in the raw EVR YAML file. Differing from the CMD and TLM
    dictionaries, this reader does not add any processing layers to
    the read.
    """
    def __init__(self, filename=None):
        try:
            if filename is None:
                self.filename = bliss.config.evrdict.filename
            else:
                self.filename = filename

            self.evrs = self.read(self.filename)

        except IOError, e:
            msg = "Could not load EVR YAML '%s': '%s'"
            log.error(msg, filename, str(e))

    def read(self, filename):
        if self.filename is None:
            self.filename = filename

        with open(self.filename, 'rb') as stream:
            out = yaml.load(stream)

        return out


def getDefaultSchema():
    return pkg_resources.resource_filename('bliss.core', 'data/evr_schema.json')

def getDefaultDict(reload=False):
    d = util.getDefaultDict(__name__, 'evrdict', EVRReader, reload)
    return d.evrs

def getDefaultEVRs():
    return getDefaultDict()

def getDefaultDictFilename():
    return bliss.config.evrdict.filename


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
                bliss.core.log.error(msg)
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
