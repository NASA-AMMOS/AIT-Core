EVRs Introduction
=================

AIT provides support for YAML-based configuration of Event Verification Records (EVRs) within the system. Below is an example of a simple set of EVRs defined for use in the toolkit.

.. code-block:: yaml

   - !EVR
     name: NO_ERROR
     code: 0x0001
     desc: No error
     message: "No error"

   - !EVR
     name: EVR_1
     code: 0x0002
     desc: EVR 1
     message: "The first evr"

   - !EVR
     name: EVR_2
     code: 0x0003
     desc: EVR 2
     message: "The second evr"

   - !EVR
     name: EVR_3
     code: 0x0004
     desc: EVR 3
     message: "The third evr %s"

Message Formatting
------------------

AIT EVRs allow you to include common format strings in the **message** attribute so that EVR data can be decoded and included in displays. You can use the :meth:`ait.core.evr.EVRDefn.format_message` method for this.

>>> import ait.core.evr
>>> evr = ait.core.evr.getDefaultDict()[3]
>>> evr.message
'The third evr %s'

We'll need a :func:`bytearray` of data to decode:

>>> data = bytearray([0x69, 0x73, 0x20, 0x74, 0x68, 0x65, 0x20, 0x67, 0x72, 0x65, 0x61, 0x74, 0x65, 0x73, 0x74, 0x21, 0x00])

We can now decode that data and include it in our message:

>>> evr.format_message(data)
'The third evr is the greatest!'

!EVR
----

name:
    The EVR's name

code:
    The code that specifies this EVR

desc (optional):
    A human readable description of what the EVR represents

message (optional):
    A human readable description of what the EVR represents. The message attribute can contain **printf** strings. The :class:`ait.core.evr.EVRDefn` class provides an interface for unpacking data into it's message attribute.
