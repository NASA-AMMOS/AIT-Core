# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Event Record (EVR) Reader

The bliss.core.evr module is used to read the EVRs from a YAML file.

Also includes deprecated EVRParser class for parsing the EVR
information from the FSW EVR classes.

"""

import os
import re
import yaml

import bliss
from bliss.core import log, util


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
    return os.path.join(bliss.config._directory, 'evr_schema.json')

def getDefaultDict(reload=False):
    d = util.getDefaultDict(__name__, 'evrdict', EVRReader, reload)
    return d.evrs

def getDefaultEVRs():
    return getDefaultDict()

def getDefaultDictFilename():
    return bliss.config.evrdict.filename


class EVRDefn(object):
    """"""
    __slots__ = ["name", "code", "desc", "_message"]

    def __init__(self, *args, **kwargs):
        """Creates a new EVR Definition."""
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))

    def __repr__(self):
        return util.toRepr(self)

    def toDict(self):
        return {
            k:getattr(self, k)
            for k in self.__slots__
        }

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        self._message = value

def YAMLCtor_EVRDefn(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    fields['argdefns'] = fields.pop('arguments', None)
    return EVRDefn(**fields)

yaml.add_constructor('!EVR' , YAMLCtor_EVRDefn)
