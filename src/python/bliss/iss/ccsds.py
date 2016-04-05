"""
ISS CCSDS Packets

The bliss.iss.ccsds module provides a representation for ISS CCSDS
packet headers using the underlying bliss.pkt module.
"""

"""
Authors: Ben Bornstein

Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.   
"""

import datetime


from bliss import dmc
from bliss import pkt


TimeFineFactor = (1e6 - 1) / 255.0


def timeFine (microseconds):
    """Converts microseconds [0 99999] to ISS fine time [0 255]."""
    return int( round(microseconds / TimeFineFactor) )


def timeMicroseconds (fine):
    """Converts ISS fine time [0 255] to integer microseconds [0 99999]."""
    return fine * TimeFineFactor


@pkt.FldMap
class EthernetHeader (pkt.Pkt):
    FieldList = [
        pkt.FldDefn( 'version'      ,   0, 'B'   , 0b11100000         ),
        pkt.FldDefn( 'type'         ,   0, 'B'   , 0b00010000         ),
        pkt.FldDefn( 'secondary'    ,   0, 'B'   , 0b00001000         ),
        pkt.FldDefn( 'apid'         ,   0, '>H'  , 0b0000011111111111 ),
        pkt.FldDefn( 'seqflags'     ,   2, 'B'   , 0b11000000         ),
        pkt.FldDefn( 'seqcount'     ,   2, '>H'  , 0b0011111111111111 ),
        pkt.FldDefn( 'length'      ,    4, '>H'                       ),
        pkt.FldDefn( 'timeCoarseMSB',   6, '>H'                       ),
        pkt.FldDefn( 'timeCoarseLSB',   8, '>H'                       ),
        pkt.FldDefn( 'timeFine'     ,  10, 'B'                        ),
        pkt.FldDefn( 'timeID'       ,  11, 'B'   , 0b11000000         ),
        pkt.FldDefn( 'checkword'    ,  11, 'B'   , 0b00100000         ),
        pkt.FldDefn( 'zoe'          ,  11, 'B'   , 0b00010000         ),
        pkt.FldDefn( 'packetType'   ,  11, 'B'   , 0b00001111         ),
        pkt.FldDefn( 'elementID'    ,  12, 'B'   , 0b01111000         ),
        pkt.FldDefn( 'endpointID'   ,  13, 'B'                        ),
        pkt.FldDefn( 'commandID'    ,  14, 'B'   , 0b11111110         ),
        pkt.FldDefn( 'systemCmd'    ,  14, 'B'   , 0b00000001         ),
        pkt.FldDefn( 'functionCode' ,  15, 'B'   ,                    ),
        pkt.FldDefn( 'reserved'     ,  16, '>H'                       ),
        pkt.FldDefn( 'stationMode'  ,  18, '>H'                       )
    ]

    def __init__ (self, data=None):
        """Creates a new ISS Ethernet CCSDS header packet."""
        super(EthernetHeader, self).__init__(data)


    def __repr__ (self):
        return 'bliss.iss.cssds.EthernetHeader<apid=%d, time=%s>' % (
            self.apid, self.time.isoformat())


    def init (self, dt=None):
        """Initialize the underlying packet data with sensisible defaults.

        An optional Python datetime can be used to initialize the
        CCSDS coarse and fine time fields.
        """
        # Per ISS SSP 41175-02, Revision L, Tables 3.3.2.1.1-1/2, p. 3-8.
        # Verified by OCO-3 Team at JSC SDIL/JSL on 2014-11-11.
        self._data[0:20] = bytearray(20)
        self.type        = 0b1    # Payload packet
        self.secondary   = 0b1    # Secondary Header present
        self.seqflags    = 0b11   # Unsegmented CCSDS data
        self.timeID      = 0b01   # Time of data generation
        self.checkword   = 0b0    # Only CMD packets contain checkwords
        self.zoe         = 0b0    # Not from ISS ZOE recording
        self.packetType  = 0b110  # Payload Private Science

        if isinstance(dt, datetime.datetime):
            self.time = dt

        self.length = len(self._data) - 6 - 1
        self.length = self.length if self.length >= 0 else 0


    @property
    def time (self):
        """The CCSDS secondary header time as a Python datetime."""
        seconds      = (self.timeCoarseMSB << 16) | self.timeCoarseLSB
        microseconds = timeMicroseconds(self.timeFine)
        return dmc.toLocalTime(seconds, microseconds)


    @time.setter
    def time (self, ts):
        seconds            = dmc.toGPSSeconds(ts)
        self.timeCoarseMSB = seconds >> 16
        self.timeCoarseLSB = seconds &  0xFFFF
        self.timeFine      = timeFine(ts.microsecond)

