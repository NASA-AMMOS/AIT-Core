BLISS Telemetry Dictionary Introduction
=======================================

BLISS provides support for YAML-based configuration of telemetry data within the system. BLISS uses a YAML based configuration file to define Packets and their constituent Fields.

.. code-block:: yaml

    - !Packet
      name: OCO3_1553_EHS
      fields:
        - !Field
          name:       version
          desc:       Indicates CCSDS Version-1 (does not change)
          bytes:       0
          type:       U8
          mask:       0xE0
        - !Field
          name:       type
          desc:       |
            Distinguishes between core and payload packet types to extend the
            APID space to 4032
          bytes:       0
          type:       U8
          mask:       0x10
          enum:
            0: 'Core'
            1: 'Payload'

All the valid parameters and attributes that can be present in the telemetry dictionary definition are defined in the telemetry schema file. By default this is called *tlm_schema.json* and is co-located with *config.yaml*.  BLISS also provides a command line utility for verifying that your telemetry dictionary configuration is valid given that you have a defined schema file. If you pass the ``--tlm`` or ``-t`` flag to ``./bliss-yaml-validate.py`` it will check this for you.

.. code-block:: bash

    $ ./bliss-yaml-validate.py --tlm
    016-07-27T09:36:21.408 | INFO     | Validation: SUCCESS: ...

----

!Packet
-------

The BLISS packet constructor is the parent construct for all BLISS telemetry packet definitions. It encapsulates high level metadata related to the packet along with all the fields that create the packets structure.

fields:
    A **list** of *!Field* objects that define the structure of the packet.

name (optional):
    A **string** denoting the name of this telemetry packet.

desc (optional):
    A **string** for providing a description of the packet.

----

!Field
------

name:
    A **string** denoting the name of this field in the packet.

type:
    A **string** specifying the data type for the section of the packet in which this field is located. You can see all the valid primitive types that will be accepted here by looking at ``bliss.dtype.PrimitiveTypes``. You can see examples of how *type* is used in the `Example Telemetry Packet Definition`_ section.

desc (optional):
    A **string** for providing a description of the field.

mask (optional):
    An integer (usually specified in hexadecimal) specifying the relevant bits of the field's *type* that represents the field's value.

bytes (optional):
    Specifies which byte(s) in the packet make up this field. This can be specified as a single integer or as a list of integers (in the case of a range of bytes). This is a helpful attribute if a field is comprised of a number of bits that do not easily divide into primitive data types. See the *Application Processes Indentifer* in the `Example Telemetry Packet Definition`_ section. If the current **!Field** is a mask of the previous **!Field**'s bytes you can specify that with **'@prev'**.

enum (optional):
    A **dict** of key, value pairs listing the enumeration of values for the field. The **key** matches with the value in the field. The **value** is a **string** describing what the value in the enumeration represents.

----

Example Telemetry Packet Definition
-----------------------------------

The example telemetry dictionary snipped below provides the definition for a CCSDS Packet Primary Header.

.. image:: _static/ccsds_prim_header.png

.. code-block:: yaml

    - !Packet
      name: CCSDS
      fields:
        - !Field
          name:   version
          desc:   CCSDS Version
          bytes:  0
          type:   U8
          mask:   0xE0

        - !Field
          name:   packet_type
          bytes:  0
          type:   U8
          mask:   0x10

        - !Field
          name:   secondary_header_flag
          desc:   |
            Indicates whether, or not, a Secondary Header follows the primary
            header (always set to 1)
          bytes:  0
          type:   U8
          mask:   0x08
          enum:
            0: 'Not Present'
            1: 'Present'

        - !Field
          name:   apid
          desc:   |
            Used in conjunction with packet_type to define the Logical
            Data Path
          bytes:  [0, 1]
          type:   MSB_U16
          mask:   0x07FF

        - !Field
          name:   sequence_flags
          desc:   |
            When sending commands, the sequence flags must be marked as
            unsegmented data. All other PL packets may be per source/destination
            ICDs.
          bytes:  2
          type:   U8
          mask:   0xC0
          enum:
            0: 'Continuation Segment'
            1: 'First Segment'
            2: 'Last Segment'
            3: 'Unsegmented'

        - !Field
          name:   sequence_count
          desc:   |
            Sequential count which numbers each packet on a Logical Data Path,
            i.e. a separate counter is maintained for each source-destination
            pair.
          bytes:  [2, 3]
          mask:   0x03FF
          type:   MSB_U16

        - !Field
          name:   packet_length
          desc:   |
            Sequential count which expresses the length of the remainder of the
            packet including checkword if present. The value is the number of
            bytes (octets) following the field minus 1.
          type:   MSB_U16
