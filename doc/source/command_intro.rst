BLISS Command Dictionary Introduction
=====================================

BLISS provides support for YAML-based configuration of commands with enough detail to provide verification of information (E.g., units) and encoding/decoding. The commands are constrained by the ISS 1553B command word design (64 total words with 11 reserved).

.. code-block:: yaml

    # An example command for setting the operation
    # mode of an instrument.
    --- !Command
    name:      CORE_SET_OP_MODE
    opcode:    0x0001
    subsystem: CORE
    desc:      |
      This command sets the operational mode.

    arguments:
      - !Argument
        name:  mode
        desc:  Mode
        units: none
        type:  U8
        bytes: 0
        enum:
          0: SAFE
          1: IDLE
          2: SCANNING
          3: SCIENCE

All the valid parameters and attributes that you can have in your command dictionary configuration file is controlled by the command dictionary schema file. By default this is called **cmd_schema.json**. A snippet of a schema is below. You can see that it allows for quite of bit of control over the command dictionary including nested object verification, individual attribute type checks, and required fields.

.. code-block:: javascript

    {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "title": "Command Dictionary Schema",
        "description": "Command Dictionary Schema",
        "type": "array",
        "items": {
            "required": ["command", "name", "opcode"],
            "additionalProperties": false,
            "properties": {
                "command": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                },
                "opcode": {
                    "type": "integer"
                },
                "subsystem": {
                    "type": "string"
                },
                "desc": {
                    "type": "string"
                },
                "arguments": {
                    ... Nested Argument and Fixed Field Schemas snipped
                }
            }
        }
    }

BLISS also provides a command line utility for verifying that your command dictionary configuration is valid given that you have a defined schema file. If you pass the ``--cmd`` or ``-c`` flag to ``./bliss-yaml-validate.py`` it will check this for you.

.. code-block:: bash
    
    $ ./bliss-yaml-validate.py --cmd
    016-07-27T09:36:21.408 | INFO     | Validation: SUCCESS: ...

BLISS provides command encoding/decoding via :class:`bliss.cmd.CmdDict`.

    >>> cmddict = bliss.cmd.getDefaultDict()
    >>> type(cmddict)
    <class 'bliss.cmd.CmdDict'>

You can create and encode a command directly from the command dictionary.

    >>> noop = cmddict.create('NO_OP')
    >>> type(noop)
    <class 'bliss.cmd.Cmd'>
    >>> noop
    NO_OP
    >>> bin_noop = noop.encode()
    >>> bin_noop
    bytearray(b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

Given a binary blob, you can also decode into a command.

    >>> decoded_cmd = cmddict.decode(bin_noop)
    >>> type(decoded_cmd)
    <class 'bliss.cmd.Cmd'>
    >>> decoded_cmd
    NO_OP


----

!Command
--------

The BLISS command constructor is the parent construct for all BLISS command definitions. It encapsulates optional arguments and contains metadata critical to the command.

name:
    A **string** denoting the name of this command

opcode:
    The number assigned to this opcode. This is usually given in hexadecimal.

subsystem (optional):
    A **string** denoting the subsystem associated with this command.

desc (optional):
    A **string** for providing a description of the command.

arguments (optional):
    A **list** of *!Argument* or *!Fixed* objects

----

!Argument
---------

The argument constructor allows for a number of parameter to specify options for a command. By default an argument needs to include a name, data type, and byte information.

name:
    A **string** denoting the name of this argument

type:
    A **string** specifying the data type of the argument. You can see all the valid primitive types that will be accepted here by looking at ``bliss.dtype.PrimitiveTypes``.

bytes:
    Specifies which byte(s) in the command filled by this argument. This can be specified as a single integer or as a list of integers (in the case of a range of bytes).

desc (opitonal):
    A **string** for providing a description of the argument.

units (optional):
    A **string** denoting the argument's units.

range (optional):
    A **list** of 2 items specifying the range of acceptable values for the argument.

enum (optional):
    A **dict** of key, value pairs listing the enumeration of valid values for the argument. The **key** matches with the value in the command. The **value** is a **string** describing what the value in the enumeration represents.

----

!Fixed
------

The fixed constructor allows you to define constant values in your command.

name:
    A **string** denoting the name of this constant.

bytes:
    Specifies which byte(s) in the command filled by this constant. This can be specified as a single integer or as a list of integers (in the case of a range of bytes).

value:
    A number specifying the value for this constant.

desc (optional):
    A **string** for providing a description of the constant.

units (optional):
    A **string** denoting the constant's units.

bytes (optional):
    Specifies which byte(s) in the command filled by this constant. This can be specified as a single integer or as a list of integers (in the case of a range of bytes).

----

Example Command Definition
--------------------------

Below is an example of what you might have defined for a command. It uses most of the options mentioned above.

.. code-block:: yaml

    --- !Command
    name:      EXAMPLE_RESET_SYSTEM
    opcode:    0x1337
    subsystem: ExampleSubSystem
    title:     Example Reset System
    desc:      |
      Reset the processor and initiate boot process.
    arguments:
      - !Fixed
        type:  LSB_U16
        bytes: [0, 1]
        value: 0x92ea
        
      - !Fixed
        type:  LSB_U16
        bytes: [2, 3]
        value: 0x3010

      - !Argument
        name:  reset_type
        desc:  |
          Reset type
          PROM_REBOOT: Nominal reboot
          DIAG_RAM_REBOOT: Diagnostic reboot
        units: none
        type:  LSB_U16
        bytes: [4, 5]
        enum:
          0x1000: PROM_REBOOT
          0x0001: DIAG_RAM_REBOOT
        
      - !Fixed
        type:  LSB_U16
        bytes: [6, 7]
        value: 0x0000
        
      - !Fixed
        type:  LSB_U16
        bytes: [8, 9]
        value: 0x0000
        
      - !Fixed
        type:  LSB_U16
        bytes: [10, 11]
