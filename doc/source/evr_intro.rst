EVRs
====

BLISS provides support for YAML-based configuration of EVRs within the system. Below is an example of a simple set of EVRs.

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

----

!EVR
----

name:
    The EVR's name

code:
    The code that specifies this EVR

desc (optional): 
    A human readable description of what the EVR represents

message (optional):
    A human readable description of what the EVR represents. The message attribute can contain **printf** strings. The :class:`bliss.core.evr.EVRDefn` class provides an interface for unpacking data into it's message attribute.
