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


"""
Consultative Committee for Space Data Systems (CCSDS)

The ait.core.ccsds module provides CCSDS header definitions and
datatypes.
"""


from ait.core import json, tlm, util


class CcsdsDefinition(json.SlotSerializer, object):
    """A :class:`CcsdsDefinition` is analogous to a
    :class:`PacketDefinition`, except it defines the expected values
    in a CCSDS header.

    :class:`CcsdsDefinition`s are most often specified in a ``ccsds:``
    block within a YAML ``!Command`` or ``!Packet`` definition.
    """

    __slots__ = 'version', 'type', 'secondary', 'apid', 'seqflags', 'length'

    def __init__(self, *args, **kwargs):
        self.version   = kwargs.get('version'  , 0)
        self.type      = kwargs.get('type'     , 0)
        self.secondary = kwargs.get('secondary', None)
        self.apid      = kwargs.get('apid'     , 0)
        self.seqflags  = kwargs.get('seqflags' , 3)  # No segmentation
        self.length    = kwargs.get('length'   , 0)

    def __repr__(self):
        return util.toRepr(self)

    @property
    def shflag(self):
        """Indicates whether a CCSDS Secondary Header is present."""
        return 1 if self.secondary else 0


class CcsdsHeader(tlm.Packet):
    """A :class:`CcsdsHeader` is just like any other :class:`Packet`,
    except that the CCSDS (primary) header :class:`FieldDefinition`s
    are already defined.  That is, there is no need to pass in a
    :class`PacketDefinition` at initialization, only the underlying
    packet data to decode as a CCSDS header.
    """

    # NOTE: CcsdsHeader.Definition is distinct from a CcsdsDefinition.
    # The former specifies how to decode the fields of a CCSDS header.
    # The latter defines the expected values for those fields within a
    # a particular type of packet.

    Definition = tlm.PacketDefinition(
        name   = 'CCSDS_Header',
        fields = [
            tlm.FieldDefinition(
                name  = 'version',
                bytes = 0,
                type  = 'U8',
                mask  = 0xE0
            ),
            tlm.FieldDefinition(
                name  = 'type',
                bytes = 0,
                type  = 'U8',
                mask  = 0x10
            ),
            tlm.FieldDefinition(
                name  = 'shflag',
                bytes = 0,
                type  = 'U8',
                mask  = 0x08
            ),
            tlm.FieldDefinition(
                name  = 'apid',
                bytes = [0, 1],
                type  = 'MSB_U16',
                mask  = 0x07FF
            ),
            tlm.FieldDefinition(
                name  = 'seqflags',
                bytes = 2,
                type  = 'U8',
                mask  = 0xC0,
                enum  = {
                    0: 'Continuation Segment',
                    1: 'First Segment',
                    2: 'Last Segment',
                    3: 'Unsegmented',
                }
            ),
            tlm.FieldDefinition(
                name  = 'seqcount',
                bytes = [2, 3],
                type  = 'MSB_U16',
                mask  = 0x3FFF
            ),
            tlm.FieldDefinition(
                name  = 'length',
                bytes = [4, 5],
                type  = 'MSB_U16'
            )
        ]
    )

    def __init__(self, data=None):
        super(CcsdsHeader, self).__init__(CcsdsHeader.Definition, data)
        self.seqflags = 3
