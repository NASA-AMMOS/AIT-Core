# Copyright 2017 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Javascript Object Notation (JSON)

The bliss.core.json module provides JSON utilities and mixin classes
for encoding and decoding between BLISS data structures and JSON.
"""

import collections
import json


def slotsToJSON(obj, slots=None):
    if slots is None:
        slots = obj.__slots__

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
    def __jsonOmit__(self, key, val):
        return val is None or val is ''

    def toJSON(self):
        return slotsToJSON(self)
