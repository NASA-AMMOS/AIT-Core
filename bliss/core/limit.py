# Copyright 2017 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Limit

The bliss.core.limit module provides limit definitions for telemetry fields.

The expected limit.yaml should follow this schema:

- !Limit
  source:   -- telemetry source for the limit. should follow format 'Packet.field_name'
  desc:     -- description of the limit
  units:    -- the units used for possible conversion depending on the units set in the
               telemetry dictionary
  lower:    -- lower limits
    error:  -- trigger error if telemetry value exceeds this lower bound (exclusive)
    warn:   -- trigger warning if telemetry value exceeds this lower bound (exclusive)
  upper:    -- upper limits
    error:  -- trigger error if telemetry value exceeds this upper bound (exclusive)
    warn:   -- trigger warning if telemetry value exceeds this upper bound (exclusive)
  value:    -- enumerated values to trigger error/warning
    error:  -- trigger error if telemetry value == or in list of strings
    warn:   -- trigger warning if telemetry value == or in list of strings

For example:

  - !Limit
    source: 1553_HS_Packet.Voltage_A
    desc: tbd
    units: Kelvin
    lower:
      error: 5.0
      warn: 10.0
    upper:
      error: 45.0
      warn: 40.0


  - !Limit
    source: Ethernet_HS_Packet.product_type
    desc: tbd
    value:
      error: FOOBAR
      warn:
        - FOO
        - BAR

"""

import os
import pkg_resources
import yaml

import bliss
from bliss.core import json, log, tlm, util

class Thresholds (json.SlotSerializer, object):
    def __init__ (self, **kwargs):
        self._thresholds = kwargs


    def __getattr__ (self, name):
        if name in self._thresholds:
            return self._thresholds[name]
        else:
            raise AttributeError("Limit has no such threshold '%s'" % name)


    def __getstate__ (self):
        return self.__dict__


    def __repr__ (self):
        kwargs = [ '%s=%s' % item for item in self._thresholds.items() ]
        return 'Thresholds(%s)' % ', '.join(kwargs)


    def __setstate__ (self, state):
        self.__dict__ = state



class LimitDefinition (json.SlotSerializer, object):
    """LimitDefinition
    """

    __slots__ = [ 'desc', 'lower', 'source', 'units', 'upper', 'value', 'source_fld' ]

    def __init__(self, *args, **kwargs):
        """Creates a new LimitDefinition."""
        self.tlmdict = tlm.getDefaultDict()

        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))

        for name in 'lower', 'upper', 'value':
            thresholds = getattr(self, name)

            if type(thresholds) is dict:
                setattr(self, name, Thresholds(**thresholds))

        if self.source:
            self.source_fld = self.get_fld_defn(self.source)

        if self.units and self.units != self.source_fld.units:
            raise SyntaxError("%s must match the units in the telemetry dictionary." % self.units)

    def __repr__(self):
        return util.toRepr(self)

    def error (self, value, units=None):
        if self.units and self.units != units:
            value = self.convert(value, units, self.units)

        check = False
        if self.lower:
            check = check or value < self.lower.error

        if self.upper:
            check = check or value > self.upper.error

        if self.value:
            if isinstance(self.value.error, list):
                check = check or value in self.value.error
            else:
                check = check or value == self.value.error

        return check

    def warn (self, value, units=None):
        if self.units and self.units != units:
            value = self.convert(value, units, self.units)

        check = False
        if self.lower:
            check = check or value < self.lower.warn

        if self.upper:
            check = check or value > self.upper.warn

        if self.value:
            if isinstance(self.value.warn, list):
                check = check or value in self.value.warn
            else:
                check = check or value == self.value.warn

        return check

    def get_fld_defn(self, source):
        pkt, fld = source.split('.')
        return self.tlmdict[pkt].fieldmap[fld]

    def convert(self, value, new_unit, old_unit):
        return value


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
