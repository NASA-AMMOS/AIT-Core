# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2017, by the California Institute of Technology.  ALL
# RIGHTS RESERVED. United States Government Sponsorship
# acknowledged. Any commercial use must be negotiated with the Office
# of Technology Transfer at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By
# accepting this software, the user agrees to comply with all
# applicable U.S. export laws and regulations. User has the
# responsibility to obtain export licenses, or other export authority
# as may be required before exporting such information to foreign
# countries or providing access to foreign persons.


import nose

from ait.core import ccsds


def testCcsdsDefinition():
    defn = ccsds.CcsdsDefinition(apid=42, length=128)

    assert defn.version   == 0
    assert defn.type      == 0
    assert defn.secondary == None
    assert defn.shflag    == 0
    assert defn.apid      == 42
    assert defn.seqflags  == 0b11
    assert defn.length    == 128


def testCcsdsHeaderDefaults():
    header = ccsds.CcsdsHeader()

    assert header.version      == 0
    assert header.type         == 0
    assert header.shflag       == 0
    assert header.apid         == 0
    assert header.raw.seqflags == 0b11
    assert header.seqcount     == 0
    assert header.length       == 0


def testCcsdsHeaderDecode():
    header = ccsds.CcsdsHeader([0x18, 0x2A, 0xC4, 0xD2, 0x16, 0x2E])

    assert header.version      == 0
    assert header.type         == 1
    assert header.shflag       == 1
    assert header.apid         == 42
    assert header.raw.seqflags == 0b11
    assert header.seqcount     == 1234
    assert header.length       == 5678


def testCcsdsHeaderEncode():
    header = ccsds.CcsdsHeader()

    header.version  = 0
    header.type     = 1
    header.shflag   = 1
    header.apid     = 42
    header.seqflags = 0b11
    header.seqcount = 1234
    header.length   = 5678

    assert header._data == bytearray([0x18, 0x2A, 0xC4, 0xD2, 0x16, 0x2E])


if __name__ == '__main__':
    nose.main()
