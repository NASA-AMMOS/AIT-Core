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
AIT Javascript Object Notation (JSON)

The ait.core.json module provides JSON utilities and mixin classes
for encoding and decoding between AIT data structures and JSON.
"""

import collections
import json


def slotsToJSON(obj, slots=None):
    """Converts the given Python object to one suitable for Javascript
    Object Notation (JSON) serialization via :func:`json.dump` or
    :func:`json.dumps`.  This function delegates to :func:`toJSON`.

    Specifically only attributes in the list of *slots* are converted.
    If *slots* is not provided, it defaults to the object's
    ``__slots__` and any inherited ``__slots__``.

    To omit certain slots from serialization, the object may define a
    :meth:`__jsonOmit__(key, val)` method.  When the method returns
    True for any particular slot name (i.e. key) and value
    combination, the slot will not serialized.
    """
    if slots is None:
        slots = list(obj.__slots__) if hasattr(obj, '__slots__') else [ ]
        for base in obj.__class__.__bases__:
            if hasattr(base, '__slots__'):
                slots.extend(base.__slots__)

    testOmit = hasattr(obj, '__jsonOmit__') and callable(obj.__jsonOmit__)
    result   = { }

    for slot in slots:
        key = slot[1:] if slot.startswith('_') else slot
        val = getattr(obj, slot, None)

        if testOmit is False or obj.__jsonOmit__(key, val) is False:
            result[key] = toJSON(val)

    return result


def toJSON (obj):
    """Converts the given Python object to one suitable for Javascript
    Object Notation (JSON) serialization via :func:`json.dump` or
    :func:`json.dumps`.  If the Python object has a :meth:`toJSON`
    method, it is always given preference and will be called to peform
    the conversion.

    Otherwise, plain mapping and sequence types are converted to
    Python dictionaries and lists, respectively, by recursively
    calling this :func:`toJSON` function on mapping keys and values or
    iterable items.  Python primitive types handled natively by the
    JSON encoder (``int``, ``long``, ``float``, ``str``, ``unicode``,
    and ``None``) are returned as-is.

    If no other conversion is appropriate, the Python builtin function
    :func:`str` is used to convert the object.
    """
    if hasattr(obj, 'toJSON') and callable(obj.toJSON):
        result = obj.toJSON()
    elif isinstance(obj, (int, long, float, str, unicode)) or obj is None:
        result = obj
    elif isinstance(obj, collections.Mapping):
        result = { toJSON(key): toJSON(obj[key]) for key in obj }
    elif isinstance(obj, collections.Sequence):
        result = [ toJSON(item) for item in obj ]
    else:
        result = str(obj)

    return result


class SlotSerializer (object):
    __slots__ = [ ]

    def __jsonOmit__(self, key, val):
        return val is None or val is ''

    def toJSON(self):
        return slotsToJSON(self)
