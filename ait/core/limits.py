# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology. ALL RIGHTS
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
AIT Limits

The ait.core.limits module provides limit definitions for telemetry fields.

The expected limits.yaml should follow this schema:

- !Limit
  source:      -- telemetry source for the limit. should follow format 'Packet.field_name'
  desc:        -- description of the limit
  units:       -- the units used for possible conversion depending on the units set in the
                  telemetry dictionary
  lower:       -- lower limits
    error:     -- trigger error if telemetry value exceeds this lower bound (exclusive)
    warn:      -- trigger warning if telemetry value exceeds this lower bound (exclusive)
  upper:       -- upper limits
    error:     -- trigger error if telemetry value exceeds this upper bound (exclusive)
    warn:      -- trigger warning if telemetry value exceeds this upper bound (exclusive)
  value:       -- enumerated values to trigger error/warning
    error:     -- trigger error if telemetry value == or in list of strings
    warn:      -- trigger warning if telemetry value == or in list of strings
  when:        -- when condition for specifying the necessary state when this limit applies
  persist:     -- number of seconds the value must persist before limits trigger

For example:

  - !Limit
    source:  1553_HS_Packet.Voltage_A
    desc:    Voltage A
    units:   Kelvin
    lower:
      error: 5.0
      warn:  10.0
    upper:
      error: 45.0
      warn:  40.0
    when:    1553_HS_Packet.BankA == 'ON'
    persist: 5


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

import ait
from ait.core import json, log, tlm, util

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

    def toJSON(self):
        return self._thresholds



class LimitDefinition (json.SlotSerializer, object):
    """LimitDefinition"""

    __slots__ = [ 'desc', 'lower', 'source', 'units', 'upper', 'value',
                    'when', 'persist' ]

    def __init__(self, *args, **kwargs):
        """Creates a new LimitDefinition."""
        for slot in self.__slots__:
            name = slot[1:] if slot.startswith("_") else slot
            setattr(self, name, kwargs.get(name, None))

        for name in 'lower', 'upper', 'value':
            thresholds = getattr(self, name)

            if type(thresholds) is dict:
                setattr(self, name, Thresholds(**thresholds))

    def __repr__(self):
        return util.toRepr(self)

    def error (self, value, units=None):
        if self.units and self.units != units:
            value = self.convert(value, units, self.units)

        check = False
        if self.lower and hasattr(self.lower, 'error'):
            check = check or value < self.lower.error

        if self.upper and hasattr(self.upper, 'error'):
            check = check or value > self.upper.error

        if self.value and hasattr(self.value, 'error'):
            if isinstance(self.value.error, list):
                check = check or value in self.value.error
            else:
                check = check or value == self.value.error

        return check

    def warn (self, value, units=None):
        if self.units and self.units != units:
            value = self.convert(value, units, self.units)

        check = False
        if self.lower and hasattr(self.lower, 'warn'):
            check = check or value < self.lower.warn

        if self.upper and hasattr(self.upper, 'warn'):
            check = check or value > self.upper.warn

        if self.value and hasattr(self.value, 'warn'):
            if isinstance(self.value.warn, list):
                check = check or value in self.value.warn
            else:
                check = check or value == self.value.warn

        return check

    def convert(self, value, new_unit, old_unit):
        return value


class LimitsDict(dict):
    """LimitsDict
    """
    def __init__(self, *args, **kwargs):
        """Creates a new Limits Dictionary from the given limits
        dictionary filename or YAML string.
        """
        self.filename = None

        if len(args) == 1 and len(kwargs) == 0 and type(args[0]) == str:
            dict.__init__(self)
            self.load(args[0])
        else:
            dict.__init__(self, *args, **kwargs)

    def add(self, defn):
        """Adds the given Limit Definition to this Limits Dictionary."""
        self[defn.source] = defn

    def load(self, content):
        """Loads Limit Definitions from the given YAML content into this
        Telemetry Dictionary.  Content may be either a filename
        containing YAML content or a YAML string.

        Load has no effect if this Limits Dictionary was already
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
    return util.getDefaultDict(__name__, 'limits', LimitsDict, reload)


def getDefaultSchema():
    return pkg_resources.resource_filename('ait.core', 'data/limits_schema.json')


def getDefaultDictFilename():
    return ait.config.limits.filename


def YAMLCtor_LimitDefinition(loader, node):
    fields = loader.construct_mapping(node, deep=True)
    return createLimitDefinition(**fields)


yaml.add_constructor('!Limit', YAMLCtor_LimitDefinition)

util.__init_extensions__(__name__, globals())
