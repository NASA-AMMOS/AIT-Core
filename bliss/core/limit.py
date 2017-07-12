# Copyright 2017 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Limit

The bliss.core.limit module provides limit definitions for telemetry fields.

The expected limit.yaml should follow this schema:

- !Limit
  source:   -- telemetry source for the limit. should follow format 'Packet.field_name'
  desc:     -- description of the limit
  error:    -- either a min/max range or an enum that will cause an error
    min:    -- min range value (exclusive)
    max:    -- max range value (exclusive)
    enum:   -- list of enumeration values that will trigger an error
  warn:     -- same as error, either a min/max range or an enum that will cause an warning
    min:    -- min range value (exclusive)
    max:    -- max range value (exclusive)
    enum:   -- list of enumeration values that will trigger an error

"""

import os
import pkg_resources
import yaml

import bliss
from bliss.core import json, log, tlm, util


class ValueDefinition(json.SlotSerializer, object):
    """ MinMaxDefinition
    """
    __slots__ = [ 'min', 'max', 'enum' ]

    def __init__(self, *args, **kwargs):
    #     """Creates a new LimitDefinition."""
        for slot in ValueDefinition.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, slot, args[0].get(name, None))

    def __repr__(self):
        return util.toRepr(self)


class LimitDefinition(json.SlotSerializer, object):
# class LimitDefinition(object):
    """LimitDefinition
    """
    __slots__ = [ 'source', 'source_fld', 'desc', 'error', 'warn' ]

    def __init__(self, *args, **kwargs):
        """Creates a new LimitDefinition."""
        self.tlmdict = tlm.getDefaultDict()

        for slot in LimitDefinition.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, slot, kwargs.get(name, None))

        if self._source:
            self.source = self._source

        if self.error:
            self.error = ValueDefinition(self.error)            

        if self.warn:
            self.warn = ValueDefinition(self.warn)

    def __repr__(self):
        return util.toRepr(self)

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        self._source = value

        self.source_fld = self.get_fld_defn(value)

    def get_fld_defn(self, source):
        pkt, fld = source.split('.')
        return self.tlmdict[pkt].fieldmap[fld]


class LimitDict(dict):
    """LimitDict
    """
    def __init__(self, *args, **kwargs):
        """Creates a new Limit Dictionary from the given limit
        dictionary filename or YAML string.
        """
        self.filename = None

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add(self, defn):
        """Adds the given Limit Definition to this Limit Dictionary."""
        self[defn.source] = defn

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
            
            limits = yaml.load(stream)

            for lmt in limits:
                self.add(lmt)

            if type(stream) is file:
                stream.close()

    def toJSON(self):
        return { name: defn.toJSON() for name, defn in self.items() }


def getDefaultDict(reload=False):
    return util.getDefaultDict(__name__, 'limit', LimitDict, reload)


def getDefaultSchema():
    return pkg_resources.resource_filename('bliss.core', 'data/limit_schema.json')


def getDefaultDictFilename():
    return bliss.config.limit.filename


def YAMLCtor_LimitDefinition(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    return createLimitDefinition(**fields)


yaml.add_constructor('!Limit', YAMLCtor_LimitDefinition)

util.__init_extensions__(__name__, globals())
