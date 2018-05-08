# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2013, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

import nose
import struct

from ait.core import cmd, dtype


CMDDICT_TEST = """
- !Command
  name:      SEQ_ENABLE_DISABLE
  opcode:    0x0042
  arguments:
    - !Argument
      name:  sequence_id
      type:  MSB_U16
      bytes: [0, 1]

    - !Argument
      name:  enable
      type:  U8
      bytes: 2
      enum:
        0: DISABLED
        1: ENABLED
"""


def testArgDefn ():
    name = 'SEQ_ENABLE_DISABLE'
    defn = cmd.CmdDict(CMDDICT_TEST)[name]

    arg  = defn.argdefns[0]
    assert arg.bytes   == [0, 1]
    assert arg.desc    == None
    assert arg.enum    == None
    assert arg.fixed   == False
    assert arg.name    == 'sequence_id'
    assert arg.nbytes  == 2
    assert arg.range   == None
    assert arg.slice() == slice(0, 2)
    assert arg.type    == dtype.get('MSB_U16')
    assert arg.units   == None
    assert arg.value   == None

    assert type( repr(arg)    ) is str

    arg = defn.argdefns[1]
    assert arg.bytes   == 2
    assert arg.desc    == None
    assert arg.enum    == {'DISABLED': 0, 'ENABLED': 1}
    assert arg.fixed   == False
    assert arg.name    == 'enable'
    assert arg.nbytes  == 1
    assert arg.range   == None
    assert arg.slice() == slice(2, 3)
    assert arg.type    == dtype.get('U8')
    assert arg.units   == None
    assert arg.value   == None

    assert type( repr(arg)    ) is str


def testArgDefnDecode ():
    name = 'SEQ_ENABLE_DISABLE'
    defn = cmd.CmdDict(CMDDICT_TEST)[name]

    arg = defn.argdefns[0]
    assert arg.decode( struct.pack('>H', 1234) ) == 1234

    arg = defn.argdefns[1]
    assert arg.decode( struct.pack('>B', 0) ) == 'DISABLED'
    assert arg.decode( struct.pack('>B', 1) ) == 'ENABLED'
    assert arg.decode( struct.pack('>B', 2) ) == 2


def testArgDefnEncode ():
    name = 'SEQ_ENABLE_DISABLE'
    defn = cmd.CmdDict(CMDDICT_TEST)[name]

    arg = defn.argdefns[0]
    assert arg.encode(1234) == struct.pack('>H', 1234)

    arg = defn.argdefns[1]
    assert arg.encode( 'DISABLED') == struct.pack('>B', 0)
    assert arg.encode( 'ENABLED' ) == struct.pack('>B', 1)
    assert arg.encode( 2         ) == struct.pack('>B', 2)


def testArgDefnValidate ():
    name = 'SEQ_ENABLE_DISABLE'
    defn = cmd.CmdDict(CMDDICT_TEST)[name]

    arg = defn.argdefns[0]
    assert arg.validate(1)   == True
    assert arg.validate(1.2) == False

    arg.range = [0, 2]
    assert arg.validate(0) == True
    assert arg.validate(1) == True
    assert arg.validate(2) == True
    assert arg.validate(3) == False

    arg = defn.argdefns[1]
    assert arg.validate('ENABLED' ) == True
    assert arg.validate('DISABLED') == True
    assert arg.validate('FOOBAR')   == False

    msgs = [ ]
    assert arg.validate('FOOBAR', msgs) == False
    assert len(msgs) > 0


def testCmdDefn ():
    name = 'SEQ_ENABLE_DISABLE'
    defn = cmd.CmdDict(CMDDICT_TEST)[name]

    assert defn.name   == name
    assert defn.opcode == 0x0042
    assert defn.nargs  == 2


def testGetDefaultDict ():
    cmddict = cmd.getDefaultDict()

    assert cmddict is not None
    assert isinstance(cmddict, cmd.CmdDict)


if __name__ == '__main__':
    nose.main()
