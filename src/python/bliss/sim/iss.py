"""
BLISS International Space Station (ISS) C&DH Simulator


The bliss.sim.iss module provides an ISS C&DH simulator and various utility
functions and classes.
"""

"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import os
import datetime
import array
import struct
import re
import csv
import cStringIO
import cPickle
import socket
import gevent

import yaml

from bliss import bti
from bliss import dmc
from bliss import gds
from bliss import log
from bliss import pkt
from bliss import util
from bliss import pcap


APID = 0  # H & S telemetry is accepted as APID 0.

sto_source = None
session_epoch = None


class Msg (object):
  def __init__ (self, api, listaddr=-1, schndx=-1):
    self.api      = api
    self.listaddr = listaddr
    self.schndx   = schndx


  def isReady (self):
    """Indicates whether or not this Msg is ready to be updated.

    Since Ballard message structures are reused, they only become
    ready (for update and send) when the previous message has been
    sent.  See also update().
    """
    return self.schndx > 0 and self.api.CmdSkipRd(self.schndx)


  def schedule (self, **kwargs):
    """Inserts this message into the next available slot in the 1553B
    Bus Controller Schedule and returns the schedule index of the
    newly created schedule entry, or a negative value if an error
    occurred.

    This function works for both regular 1553 messages and for lists of
    messages (listaddr).

    In the case of listaddr messages the schedule call will mark the listaddr
    to be logged by the event log. This logging is used by the ISS sim to keep
    track of broadcast sync message frames.
    """
    result = -1

    if self.schndx > 0:
      result = self.api.BCSchedCall(bti.COND1553_ALWAYS, self.schndx)
      if 'oneshot' in kwargs:
        self.oneshot = kwargs['oneshot']
      if 'skip' in kwargs:
        self.skip    = kwargs['skip']
    elif self.listaddr > 0:
      # A listaddr does not have a schedule index, so it can't be skipped or
      # turned into a one shot
      if len(kwargs) > 0:
        raise(bti.BTIError(-1))

      result = self.api.BCSchedMsg(self.listaddr)
      # Also, schedule a log message
      self.api.BCSchedLog(bti.COND1553_ALWAYS, self.listaddr & 0xfff)
    return result


  @property
  def skip(self):
    """Returns the skip value of the 1553 message"""
    if self.schndx <= 0:
      raise bti.BTIError(-1)

    return self.api.CmdSkipRd(self.schndx)

  @skip.setter
  def skip(self, value):
    """Sets the skip value of the 1553 message"""
    if self.schndx <= 0:
      raise bti.BTIError(-1)
    elif value == 0 or value == 1:
      self.api.CmdSkipWr(value, self.schndx)
    else:
      raise TypeError("value has to be 0 or 1")


  @property
  def oneshot(self):
    """Returns the one shot value of the 1553 message"""
    if self.schndx <= 0:
      raise bti.BTIERROR(-1)

    return self.api.CmdShotRd(self.schndx)

  @oneshot.setter
  def oneshot(self, value):
    """Sets the one shot value of the 1553 message"""
    if self.schndx <= 0:
      raise bti.BTIError(-1)
    elif value == 0 or value == 1:
      self.api.CmdShotWr(value, self.schndx)
    else:
      raise TypeError("value has to be 0 or 1")


  def send (self):
    """Marks this message as ready to be sent.  The time at which the
    message is sent is controlled by the 1553B bus schedule.
    """
    self.skip = 0



class BADMsg (Msg):
  def __init__ (self, api):
    super(BADMsg, self).__init__(api)
    self.data  = (bti.WORD * 32)()
    self.msg13 = api.BCCreateMsg(cwd1=(31, 0, 13, 32))
    self.msg14 = api.BCCreateMsg(cwd1=(31, 0, 14, 32))
    # We want to keep one per object packet so we can have a consistent CCSDS
    # header
    self.hdr_pkt = BADPkt(bytearray(128), True)

    schndx = api.BCSchedMsg(self.msg13)
    api.BCSchedMsg(self.msg14)
    api.BCSchedReturn()

    self.schndx = api.BCSchedCall(bti.COND1553_ALWAYS, schndx)
    api.BCSchedReturn()


  def update (self, frame, time):
    """Transmits BAD to the ISS payload."""
    self.hdr_pkt.time = time
    self.hdr_pkt.secondary = 1
    pkt = sto_source.build_pkt(frame % 10)

    # Get the CCSDS header information from our packet for just that purpose
    self.data[0:8] = self.hdr_pkt.words[0:8]
    """The BAD message on the 1553 bus is a 64 word message. That means it
    spans two 1553 messages. This extracts the front half from our internal
    packet."""
    self.data[8:32] = pkt.words[8:32]
    self.api.MsgDataWr(self.data, self.msg13)

    """The second message extracted from our internal packet"""
    self.data[:] = pkt.words[32:]
    self.api.MsgDataWr(self.data, self.msg14)

    self.send()
    self.hdr_pkt.increment()


class FloatToByte (object):
  """The time fine field is a floating point number in the BAD csv STO file but
  is stored as a byte in the BAD packet on 1553. This class allows the
  conversion between for the pkt.Pkt class just like pkt.Bitfield."""
  def __init__(self, multi=0.004):
    self._multi = multi  # Multiplier for the byte

  def tovalue(self, inbyte):
    value = float(self._multi * inbyte)
    return value

  def fromvalue(self, value, outbyte):
    value = value / self._multi
    fixed_value = int(value)
    if fixed_value > 255:
      fixed_value = 255
    elif fixed_value < 0:
      fixed_value = 0

    outbyte = fixed_value
    return outbyte


@pkt.FldMap
class BADPkt (pkt.Pkt):
  """An ISS PL MDM Broadcast Ancillary Data (BAD) packet."""

  FieldList = [
    pkt.FldDefn( "version"      ,   0, "B"   , pkt.Bitfield(0xe0)),
    pkt.FldDefn( "type"         ,   0, "B"   , pkt.Bitfield(0x10)),
    pkt.FldDefn( "secondary"    ,   0, "B"   , pkt.Bitfield(0x8)),
    pkt.FldDefn( "apid"         ,   0, ">H"  , pkt.Bitfield(0x7ff) ),
    pkt.FldDefn( "seqflags"     ,   2, "B"   , pkt.Bitfield(0xc0)),
    pkt.FldDefn( "seqcount"     ,   2, ">H"  , pkt.Bitfield(0x3fff)),
    pkt.FldDefn( "length"       ,   4, ">H"                        ),
    pkt.FldDefn( "timeCoarseMSB",   6, ">H"                        ),
    pkt.FldDefn( "timeCoarseLSB",   8, ">H"                        ),
    pkt.FldDefn( "timeFine"     ,  10, "B"                         ),
    pkt.FldDefn( "timeID"       ,  11, "B"   , pkt.Bitfield(0xc0)),
    pkt.FldDefn( "checkword"    ,  11, "B"   , pkt.Bitfield(0x20)),
    pkt.FldDefn( "zoe"          ,  11, "B"   , pkt.Bitfield(0x10)),
    pkt.FldDefn( "packetType"   ,  11, "B"   , pkt.Bitfield(0xf)),
    pkt.FldDefn( "elementID"    ,  12, "B"   , pkt.Bitfield(0x78)),
    pkt.FldDefn( "dataPkt"      ,  12, "B"   , pkt.Bitfield(0x4)),
    pkt.FldDefn( "versionID"    ,  12, ">H"  , pkt.Bitfield(0x3c0) ),
    pkt.FldDefn( "formatID"     ,  13, "B"   , pkt.Bitfield(0x3f)),
    pkt.FldDefn( "frameID"      ,  15, "B"   , pkt.Bitfield(0x7f)),
    pkt.FldDefn( "hiRate"       ,  16, ">36H"                      ),
    pkt.FldDefn( "loRate"       ,  88, ">20H"                      ),
    pkt.FldDefn( "CDT_PS_PDtimetagCoarse", 16, ">l"                ),
    pkt.FldDefn( "CDT_PS_PDtimetagFine"  , 20, "B", FloatToByte()  ),
    pkt.FldDefn( "CDT_PS_PDInertPosX"    , 22, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertPosY"    , 26, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertPosZ"    , 30, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertVelX"    , 34, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertVelY"    , 38, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertVelZ"    , 42, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertAttQ0"   , 46, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertAttQ1"   , 50, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertAttQ2"   , 54, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDInertAttQ3"   , 58, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDRateX"        , 64, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDRateY"        , 68, "f"                 ),
    pkt.FldDefn( "CDT_PS_PDRateZ"        , 72, "f"                 ),
    pkt.FldDefn( "STS_PS_PDAttitudeRateQuality", 73, "B", pkt.Bitfield(0x3 )),
    pkt.FldDefn( "STS_PS_PDSolarLOSQuality"    , 73, "B", pkt.Bitfield(0xc )),
    pkt.FldDefn( "STS_PS_PDAttitudeQuality"    , 73, "B", pkt.Bitfield(0x30)),
    pkt.FldDefn( "STS_PS_PDOrbitalStateQuality", 73, "B", pkt.Bitfield(0xc0)),
    pkt.FldDefn( "CDT_PS_PDSolarLOSX", 16, "f"),
    pkt.FldDefn( "CDT_PS_PDSolarLOSY", 20, "f"),
    pkt.FldDefn( "CDT_PS_PDSolarLOSZ", 24, "f"),
    pkt.FldDefn( "SARJ_M_BAD_DATA_FLOAT_PORT_JOINT_ANGLE_READOUT", 48, "f"),
    pkt.FldDefn( "SARJ_M_BAD_DATA_FLOAT_STBD_JOINT_ANGLE_READOUT", 52, "f"),
    pkt.FldDefn( "CDT_GCM_Time_Error_Seconds", 80, "f"),
    pkt.FldDefn( "CDT_GCM_Time_Error_Seconds", 84, "f")
  ]

  _epoch_delta = datetime.timedelta()

  def __init__ (self, data, init=False):
    """Creates a new ISS PL MDM BAD packet containing the given raw
    packet data.

    If init is True, the underlying packet data CCSDS header fields
    will be initialized for ISS command packets.
    """
    super(BADPkt, self).__init__(data)

    BADPkt.reset_time()

    if init:
      self._data[0:20] = bytearray(20)
      self.type        = 0b0
      self.secondary   = 0b1
      self.seqflags    = 0b11
      self.apid        = 0x0C0
      self.length      = 128 - 6 - 1
      self.time        = datetime.datetime.utcnow() - BADPkt._epoch_delta
      self.timeID      = 0b01
      self.checkword   = 0b0
      self.zoe         = 0b0
      self.packetType  = 0b0111

      # Word #7
      # SSP 52050J: Appendix E: Summary of CCSDS Secondary Header Tailoring
      #   A.2. Word #7: Per SSP 41175-02, Paragraph 3.3.2.1.1, Figure
      #   3.3.2.1.1-2 and Table 3.3.2.1.1-2. The Packet ID-Element ID will
      #   contain a value of '0001B' (NASA) per Table 3.3.2.1.1-2 of SSP
      #   41175-02.
      self.elementID   = 0b0001

      self.dataPkt     = 0b1
      self.versionID   = 0b0001
      self.formatID    = 11
      self.frameID     = 0


  @classmethod
  def reset_time(cls):
    if session_epoch is not None:
      cls._epoch_delta = datetime.datetime.utcnow() - session_epoch

  @property
  def time (self):
    """The CCSDS secondary header time as a Python datetime."""
    seconds      = (self.timeCoarseMSB << 16) | self.timeCoarseLSB
    microseconds = self.timeFine * 3937
    return dmc.toLocalTime(seconds, microseconds)


  @time.setter
  def time (self, timestamp):
    seconds            = dmc.toGPSSeconds(timestamp)
    self.timeCoarseMSB = seconds >> 16
    self.timeCoarseLSB = seconds &  0xFFFF
    self.timeFine      = timestamp.microsecond / 3937


  def increment (self):
    """Increments the CCSDS packet sequence count."""
    self.seqcount = (self.seqcount + 1) % 16384
    self.frameID  = (self.frameID  + 1) % 100


class CmdMsg (Msg):
  """CmdMsg implements ISS Payload MDM 1553B command messages.

  According to SSP 52050 Rev. J, Section 3.2.3.4 Commanding:

      On each PL MDM local bus, commands to the ISPR are transferred
      from the PL MDM through two 32-word messages (i.e., a 64 word
      command packet) in each 100 millisecond processing frame through
      the two consecutive subaddresses shown in Table 3.2.3.2.1.4-1

  Table 2.3.2.2.1.4-1 shows commands are sent on subaddress 8 and 9.
  """


  def __init__ (self, api, rtaddr):
    """Creates a new ISS Payload MDM 1553B Command Message.

    The api parameter is the Ballard BTI API object (created via
    bti.BTI1553(card)).  Command Messages will be sent to the payload
    at the given remote terminal address (rtaddr).

    To schedule this message, see schedule().
    """
    super(CmdMsg, self).__init__(api)
    self.data = (bti.WORD * 32)()
    self.msg8 = api.BCCreateMsg(cwd1=(rtaddr, 0, 8, 32))
    self.msg9 = api.BCCreateMsg(cwd1=(rtaddr, 0, 9, 32))
    self.pkt  = CmdPkt(bytearray(128), True)

    schndx = api.BCSchedMsg(self.msg8)
    api.BCSchedMsg(self.msg9)
    api.BCSchedReturn()

    self.schndx = api.BCSchedCall(bti.COND1553_ALWAYS, schndx)
    api.BCSchedReturn()


  def update (self, time, cmd):
    """Transmits the given command to the ISS payload."""
    self.pkt.time    = time
    self.pkt.command = cmd
    self.pkt.updateChecksum()

    self.data[0:32] = self.pkt.words[0:32]
    self.api.MsgDataWr(self.data, self.msg8)

    self.data[0:32] = self.pkt.words[32:]
    self.api.MsgDataWr(self.data, self.msg9)

    args = (len(self.pkt), self.pkt.seqcount)
    log.debug("Command sent     (bytes=%d, seqcount=%d)" % args)
    gds.hexdump(self.pkt.bytes, preamble="Command: ", addr=0)

    self.send()
    self.pkt.increment()



@pkt.FldMap
class CmdPkt (pkt.Pkt):
  """An ISS PL MDM command packet."""

  FieldList = [
    pkt.FldDefn( "version"      ,   0, "B"   , pkt.Bitfield(0b11100000)         ),
    pkt.FldDefn( "type"         ,   0, "B"   , pkt.Bitfield(0b00010000)         ),
    pkt.FldDefn( "secondary"    ,   0, "B"   , pkt.Bitfield(0b00001000)         ),
    pkt.FldDefn( "apid"         ,   0, ">H"  , pkt.Bitfield(0b0000011111111111) ),
    pkt.FldDefn( "seqflags"     ,   2, "B"   , pkt.Bitfield(0b11000000)         ),
    pkt.FldDefn( "seqcount"     ,   2, ">H"  , pkt.Bitfield(0b0011111111111111) ),
    pkt.FldDefn( "length"       ,   4, ">H"                                     ),
    pkt.FldDefn( "timeCoarseMSB",   6, ">H"                                     ),
    pkt.FldDefn( "timeCoarseLSB",   8, ">H"                                     ),
    pkt.FldDefn( "timeFine"     ,  10, "B"                                      ),
    pkt.FldDefn( "timeID"       ,  11, "B"   , pkt.Bitfield(0b11000000)         ),
    pkt.FldDefn( "checkword"    ,  11, "B"   , pkt.Bitfield(0b00100000)         ),
    pkt.FldDefn( "zoe"          ,  11, "B"   , pkt.Bitfield(0b00010000)         ),
    pkt.FldDefn( "packetType"   ,  11, "B"   , pkt.Bitfield(0b00001111)         ),
    pkt.FldDefn( "elementID"    ,  12, "B"   , pkt.Bitfield(0b01111000)         ),
    pkt.FldDefn( "endpointID"   ,  13, "B"                                      ),
    pkt.FldDefn( "commandID"    ,  14, "B"   , pkt.Bitfield(0b11111110)         ),
    pkt.FldDefn( "systemCmd"    ,  14, "B"   , pkt.Bitfield(0b00000001)         ),
    pkt.FldDefn( "functionCode" ,  15, "B"   ,                                  ),
    pkt.FldDefn( "reserved"     ,  16, ">H"                                     ),
    pkt.FldDefn( "stationMode"  ,  18, ">H"                                     ),
    pkt.FldDefn( "command"      ,  20, "106s"                                   ),
    pkt.FldDefn( "checksum"     , 126, ">H"                                     )
  ]

  _epoch_delta = datetime.timedelta()

  def __init__ (self, data, init=False):
    """Creates a new ISS PL MDM command packet containing the given
    raw packet data.

    If init is True, the underlying packet data CCSDS header fields
    will be initialized for ISS command packets.
    """
    super(CmdPkt, self).__init__(data)

    CmdPkt.reset_time()

    if init:
      self._data[0:20] = bytearray(20)
      self.type        = 0b1
      self.secondary   = 0b1
      self.seqflags    = 0b11
      self.apid        = 0x0C0
      self.length      = 128 - 6 - 1
      self.time        = datetime.datetime.utcnow() - CmdPkt._epoch_delta
      self.timeID      = 0b01
      self.checkword   = 0b1
      self.zoe         = 0b0
      self.packetType  = 0b1010

      # Word #7
      # SSP 52050J: Appendix E: Summary of CCSDS Secondary Header Tailoring
      #   A.2. Word #7: Per SSP 41175-02, Paragraph 3.3.2.1.1, Figure
      #   3.3.2.1.1-2 and Table 3.3.2.1.1-2. The Packet ID-Element ID will
      #   contain a value of '0001B' (NASA) per Table 3.3.2.1.1-2 of SSP
      #   41175-02.
      self.elementID   = 0b0001


  @classmethod
  def reset_time(cls):
    if session_epoch is not None:
      cls._epoch_delta = datetime.datetime.utcnow() - session_epoch

  @property
  def time (self):
    """The CCSDS secondary header time as a Python datetime."""
    seconds      = (self.timeCoarseMSB << 16) | self.timeCoarseLSB
    microseconds = self.timeFine * 3937
    return dmc.toLocalTime(seconds, microseconds)


  @time.setter
  def time (self, timestamp):
    seconds            = dmc.toGPSSeconds(timestamp)
    self.timeCoarseMSB = seconds >> 16
    self.timeCoarseLSB = seconds &  0xFFFF
    self.timeFine      = timestamp.microsecond / 3937


  def increment (self):
    """Increments the CCSDS packet sequence count."""
    self.seqcount = (self.seqcount + 1) % 16384


  def updateChecksum (self):
    """Updates the command packet checksum."""
    self.checksum = sum(self.words[:-1]) & 0xFFFF



class TimeMsg (Msg):
  """TimeMsg implements ISS Payload MDM 1553B time messages.

  According to SSP 41175-02 Rev. H, Section 3.3.2.2.2 Broadcast Time:

      The BC appends the non-CCSDS seconds/subseconds data to the time
      value in its Local Reference Clock (LRC) to build the Time
      Broadcast message. This field is computed as the one's portion
      of the seconds plus the subseconds information of the CCSDS time
      converted to a straight binary count and rounded to the nearest
      256 microseconds. The Time Broadcast should represent the actual
      BC time at the time of the broadcast.

      A.  Reserved.

      B.  The BC shall broadcast the Time Broadcast message at a 1 Hz
      rate to subaddress 29 as the first bus transaction of the third
      subframe following a 1 second crossover using the format in
      Table 3.3.2.2.2-1. (The inaccuracy of the Time Broadcast message
      received over the MDM BIA is within 20 microseconds.)

                 TABLE 3.3.2.2.2-1 BROADCAST TIME MESSAGE
                            CONTENT / FORMAT
      +--------+---------------------------------------------------+
      | Word # | Description                                       |
      +--------+---------------------------------------------------+
      |        | PUI = PD 24482                                    |
      +--------+---------------------------------------------------+
      | ...    | ...                                               |
      +--------+---------------------------------------------------+
  """

  _epoch_delta = datetime.timedelta()

  def __init__ (self, api):
    super(TimeMsg, self).__init__(api)
    self.data = (bti.WORD * 8)()
    self.msg  = api.BCCreateMsg(cwd1=(31, 0, 29, 8))
    self.time = datetime.datetime.utcnow() - TimeMsg._epoch_delta

    schndx = api.BCSchedMsg(self.msg)
    api.BCSchedReturn()

    self.schndx = api.BCSchedCall(bti.COND1553_ALWAYS, schndx)
    api.BCSchedReturn()


  def update (self, time=None):
    """Updates the ISS Payload MDM Time Message to the given Python
    datetime, defaulting to the current date and time.

    NOTE: This method should only be called when TimeMsg.ready()
    returns True.
    """
    if time is None:
      time = datetime.datetime.utcnow() - TimeMsg._epoch_delta

    self.time = time
    century   = time.year / 100
    decade    = time.year % 100
    second    = time.second + 1

    data    = self.data
    data[0] = (0x50 << 8) | util.toBCD(century)
    data[1] = (util.toBCD(decade)      << 8) | util.toBCD(time.month)
    data[2] = (util.toBCD(time.day)    << 8) | util.toBCD(time.hour)
    data[3] = (util.toBCD(time.minute) << 8) | util.toBCD(second)
    data[4] = 0x0000
    data[5] = 0x61A8  # 0.025 secs past start of second
    data[6] = 0x0000
    data[7] = 0x0000

    self.api.MsgDataWr(self.data, self.msg)
    self.send()

  @classmethod
  def reset_time (cls):
    if session_epoch is not None:
      cls._epoch_delta = datetime.datetime.utcnow() - session_epoch


class TlmMsg (Msg):
  """TlmMsg implements the ISS Payload MDM 1553B Health and Status polls. The
  H&S poll is a BC-RT message with a 1553B sub address of 9. There are four
  polls per sub-frame. The ISS PL MDM will send the first four polls in the
  first sub-frame of every 1-second frame. The PL MDM will determine how many
  polls to send in other sub-frames based on the amount of data in the CCSDS
  header that will be received in the first poll.

  This is implemented by having the sim make a list of 40 TlmMsg objects.
  Inserting them all into the frame, but making it so that the other 36
  messages are skipped. When a CCSDS header is read the sim flips the skip bit
  on the other 36 poll messages according to the number needed based on that
  header. For example if 29 messages are required for a H&S packet then the sim
  will de-assert the skip bit on poll messages 4-28 while leaving the rest
  alone."""

  WordsPerMsg = 32

  def __init__(self, api, rtaddr):
    super(TlmMsg, self).__init__(api)
    self.data = bti.MSGDATA()
    self.msg9 = api.BCCreateMsg(cwd1=(rtaddr, 1, 9, 32))

  def schedule(self, **kwargs):
    # Insert our message on sub address 9 into the schedule
    result = self.api.BCSchedMsg(self.msg9)
    # The return value is our index in the BC schedule
    self.schndx = result
    # If there are arguments, apply them
    if 'oneshot' in kwargs:
      self.oneshot = kwargs['oneshot']
    if 'skip' in kwargs:
      self.skip = kwargs['skip']

    return self.schndx

  def isHIT(self):
    # Read in the error field of my message
    retval = self.api.MsgFieldRd(bti.FIELD1553_ERROR, self.msg9)
    hitval = retval & bti.MSGERR1553_HIT
    return hitval

  def isRESP(self):
    retval = self.api.MsgFieldRd(bti.FIELD1553_ERROR, self.msg9)
    norespval = retval & bti.MSGERR1553_NORESP
    return norespval == 0

  def isDataReady(self):
    """
    If both the HIT bit is set and the NORESP bit is clear then the message has
    data
    """
    return self.isHIT() and self.isRESP()

  def clearErrFld(self):
    self.api.MsgFieldWr(0, bti.FIELD1553_ERROR, self.msg9)

  def read(self):
    # Read in my data from the BTI core using the API call for a message.
    self.api.MsgDataRd(self.data, self.msg9, TlmMsg.WordsPerMsg)
    data_ = array.array("H", self.data)
    data_.byteswap()
    for n in range(TlmMsg.WordsPerMsg):
      self.data[n] = data_[n]


@pkt.FldMap
class TlmPkt (pkt.Pkt):
  """An ISS PL/MDM telemetry packet."""

  FieldList = [
    pkt.FldDefn( "version"      ,   0, "B"   , pkt.Bitfield(0b11100000)         ),
    pkt.FldDefn( "type"         ,   0, "B"   , pkt.Bitfield(0b00010000)         ),
    pkt.FldDefn( "secondary"    ,   0, "B"   , pkt.Bitfield(0b00001000)         ),
    pkt.FldDefn( "apid"         ,   0, ">H"  , pkt.Bitfield(0b0000011111111111) ),
    pkt.FldDefn( "seqflags"     ,   2, "B"   , pkt.Bitfield(0b11000000)         ),
    pkt.FldDefn( "seqcount"     ,   2, ">H"  , pkt.Bitfield(0b0011111111111111) ),
    pkt.FldDefn( "_length"      ,   4, ">H"                                     ),
    pkt.FldDefn( "timeCoarseMSB",   6, ">H"                                     ),
    pkt.FldDefn( "timeCoarseLSB",   8, ">H"                                     ),
    pkt.FldDefn( "timeFine"     ,  10, "B"                                      ),
    pkt.FldDefn( "timeID"       ,  11, "B"   , pkt.Bitfield(0b11000000)         ),
    pkt.FldDefn( "checkword"    ,  11, "B"   , pkt.Bitfield(0b00100000)         ),
    pkt.FldDefn( "zoe"          ,  11, "B"   , pkt.Bitfield(0b00010000)         ),
    pkt.FldDefn( "packetType"   ,  11, "B"   , pkt.Bitfield(0b00001111)         ),
    pkt.FldDefn( "elementID"    ,  12, "B"   , pkt.Bitfield(0b01111000)         ),
    pkt.FldDefn( "endpointID"   ,  13, "B"                                      ),
    pkt.FldDefn( "commandID"    ,  14, "B"   , pkt.Bitfield(0b11111110)         ),
    pkt.FldDefn( "systemCmd"    ,  14, "B"   , pkt.Bitfield(0b00000001)         ),
    pkt.FldDefn( "functionCode" ,  15, "B"   ,                                  ),
    pkt.FldDefn( "reserved"     ,  16, ">H"                                     ),
    pkt.FldDefn( "stationMode"  ,  18, ">H"                                     ),
  ]


  primaryHeaderLen = 6

  @classmethod
  def pollsPerPktLen(cls, pktLenInBytes):
    adjustpoll = 0
    if (pktLenInBytes / 2) % TlmMsg.WordsPerMsg > 0:
      adjustpoll = 1

    return (pktLenInBytes / 2) / TlmMsg.WordsPerMsg + adjustpoll

  def __init__ (self, data):
    """Creates a new OCO-3 telemetry packet containing the given
    raw packet data.
    """
    super(TlmPkt, self).__init__(data)


  def isValid(self, apid):
    if (self.version != 0    or
        self.type != 1      or
        self.secondary != 1 or
        self.apid != apid):
      return False

    return True


  @property
  def time (self):
    """The CCSDS secondary header time as a Python datetime."""
    seconds      = (self.timeCoarseMSB << 16) | self.timeCoarseLSB
    microseconds = self.timeFine * 3937
    return dmc.toLocalTime(seconds, microseconds)


  @property
  def length(self):
    """The length of the entire packet is the length in the header
    + 6 octets for the primary header + 1"""
    return self._length + TlmPkt.primaryHeaderLen + 1


  @length.setter
  def length(self, length_in_octets):
    self.length = length_in_octets - TlmPkt.primaryHeaderLen - 1

  # Return the number of words the packet makes up. Note that odd number of
  # bytes require an additional partial word
  def lenInWords(self):
    return self.length / 2 + self.length % 2


class SyncMsg (Msg):
  """SyncMsg implements ISS Payload MDM 1553B broadcast synchronization
  messages with data words.

  According to SSP 41175-02 Rev. H, Section 3.3.2.2.1 Broadcast Sync:

      The BC shall broadcast a Synchronize With Data Word Mode Command
      (Mode Code 10001) and a data word containing its own current
      processing frame number as the first message of subframe number
      zero of each processing frame.

      The data word is defined by Table 3.3.2.2.1-1, Broadcast Sync
      With Data Message Content / Format Definition.

           TABLE 3.3.2.2.1-1 BROADCAST SYNC WITH DATA MESSAGE
                            CONTENT / FORMAT
      +--------+---------------------------------------------------+
      | Word # | Description                                       |
      +--------+---------------------------------------------------+
      |        | PUI = PD 24480                                    |
      +--------+---------------------------------------------------+
      |      1 | Bus Controller Processing Frame Number, an        |
      |        | integer with range 0-99, accuracy of 1, precision |
      |        | of 1                                              |
      +--------+---------------------------------------------------+
  """


  def __init__ (self, api):
    """Creates a new ISS Payload MDM 1553B Broadcast Synchronization
    Message.

    SyncMsgs are implemented as a Ballard Circular List Buffer with
    100 messages (data words 0-99).  The api parameter is the Ballard
    BTI API object (created via bti.BTI1553(card)).  To schedule this
    message, see schedule().
    """
    super(SyncMsg, self).__init__(api)
    flags         = bti.LISTCRT1553_CIRCULAR
    nmsgs         = 100
    data          = bti.MSGDATA()
    mcode         = 17
    self.listaddr = api.BCCreateList(nmsgs, flags, cwd1=(31, 0, 31, mcode))

    for m in range(nmsgs):
      data[0] = m
      api.ListDataWr(data, self.listaddr)


class BADCSV (object):
  def __init__ (self, bad_csv_filename, bad_map_filename, set_epoch=False):
    global session_epoch
    self._sto_data = list()
    self._bad_map = dict()
    self._frame_map = dict()
    self._sto_index = 0
    self._sto_first_time = True

    # If given an empty filename, assume there is nothing to do.
    if len(bad_csv_filename) == 0:
      return

    """We read in a BAD/PUI map that we can use to organize the PUI values to
    the BAD packet values"""
    log.info('BAD map file %s' % bad_map_filename)
    bmap_file = open(bad_map_filename, 'rb')
    bmap_yaml = bmap_file.read()
    self._bad_map = yaml.load(bmap_yaml)
    self._frame_map = dict()
    for key, rec in self._bad_map.iteritems():
      if rec['frame'] not in self._frame_map:
        frec = dict(rec)
        frec['pui'] = key
        pkt = BADPkt(bytearray(128), True)
        self._frame_map[rec['frame']] = ([frec], pkt)
        continue

      frec = dict(rec)
      frec['pui'] = key
      self._frame_map[rec['frame']][0].append(frec)

    pcklname = os.path.splitext(bad_csv_filename)[0] + '.pkl'
    if (os.path.exists(pcklname) and
        (os.path.getmtime(pcklname) > os.path.getmtime(bad_csv_filename))):
      log.info('Pickle cache %s is newer then the given CSV file %s'
               % (pcklname, bad_csv_filename))
      with open(pcklname, 'rb') as stream:
        self._sto_data = cPickle.load(stream)
    else:
      log.info('Loading CSV file %s' % bad_csv_filename)
      """Creates a new BAD CSV object to provide values to the ISS sim. These
      values will be inserted into the BAD messages on the 1553 bus."""
      sto_file = open(bad_csv_filename, 'rb')
      csv_file = cStringIO.StringIO()
      """The STO file is a CSV of a kind. It needs to be modified a lot to work
      well with the Python csv module."""
      first_line = True
      start_data = False
      PUIs = 0
      l_c = 0
      for line in sto_file.readlines():
        if first_line is True:
          """The first line is the header and csv will use it to determine the
          dict keys"""
          line = re.sub('status', str(), line)
          line = re.sub('^#Header\s+', '#', line)
          line = re.sub('\t+', '\t', line)
          line = line.rstrip()
          PUIs = len(line.split('\t'))
          print >>csv_file, line
          first_line = False
          l_c += 1
          continue

        if re.match('^#Start_Data', line):
          """There is no point in collecting lines before Start_Data"""
          start_data = True
          l_c += 1
          continue
        elif start_data is not True:
          l_c += 1
          continue


        if re.match('^#End_Data', line):
          """There is no point in collecting lines after End_Data"""
          start_data = False
          break

        if len(line.rstrip()) == 0:
          l_c += 1
          continue

        line = line.rstrip()
        line = re.sub('S', str(), line)
        line = re.sub(' ', str(), line)
        line = re.sub('^#Data\t', str(), line)
        line = re.sub('\t+', '\t', line)
        line = re.sub('\s+$', str(), line)

        l_c += 1
        print >>csv_file, line

      sto_file.close()
      csv_file.seek(0)
      reader = csv.DictReader(csv_file, delimiter='\t')
      for row in reader:
        new_row = dict()
        for key, val in row.items():
          if key is not None and len(key) > 0:
            if key in self._bad_map:
              new_row[key] = self.conv_rec(key, val)
            else:
              new_row[key] = val

        self._sto_data.append(new_row)

      csv_file.close()
      log.info('Dumping to pickle cache')
      with open(pcklname, 'wb') as stream:
        cPickle.dump(self._sto_data, stream, -1)

    if set_epoch is True and session_epoch is None:
      # Get the session epoch from the first entry in the STO data
      t_sec = int(self._sto_data[0]['LADP06MD2378W'])
      t_usec = int(float(self._sto_data[0]['LADP06MD2380W']) * 1000000)
      session_epoch = dmc.toLocalTime(t_sec, t_usec)
      log.info('Session epoch is %s' % session_epoch.isoformat())


  def build_pkt(self, frame):
    """Given a frame return a packet with data in it to match what should be
    sent out on 1553."""
    if frame not in self._frame_map:
      return BADPkt(bytearray(128), True)

    puis, cpkt, rec = self.update_frame(frame)
    for pui in puis:
      setattr(cpkt, pui['desc'], rec[pui['pui']])

    return cpkt

  def conv_rec(self, pui, rec_str):
    rec_type = self._bad_map[pui]['format']
    if rec_type == 'l':
      return int(rec_str)
    elif rec_type == 'f':
      return float(rec_str)
    elif rec_type == 'B':
      if 'enum' in self._bad_map[pui]:
        return self._bad_map[pui]['enum'][rec_str.lower()]
      else:
        return int(rec_type)


  def update_frame (self, frame):
    """Given a frame return the PUIs for the frame and the current record in
    the STO data series"""
    if frame not in self._frame_map:
      # Only a few frames have data that the ISS really cares about
      return (None, None, None)

    puis = self._frame_map[frame][0]
    cpkt = self._frame_map[frame][1]
    rec = self._sto_data[self._sto_index]
    if frame == 0 and self._sto_first_time is not True:
      self._sto_index = (self._sto_index + 1) % len(self._sto_data)
    elif frame == 0:
      self._sto_first_time = False

    return (puis, cpkt, rec)

  @property
  def sto_index (self):
    return self._sto_index

  @sto_index.setter
  def sto_index (self, idx):
    """Given an index, reset the current index value. This setter is provided
    to help with synchronizing the BAD with other types of telemetry. If the
    user wants to make it so that BAD starts at index second 1, this method
    allows for that."""
    self._sto_index = idx % len(self._sto_data)
    if self._sto_index == 0:
      self._sto_first_time = True

  def reset (self):
    """Convenience function to automatically set the STO index to 0."""
    self.sto_index = 0


class TlmTask(gevent.Greenlet):
  def __init__(self, iss_sim, pcap_fname=None, addr="127.0.0.1", port=3076):
    super(TlmTask, self).__init__()
    self._iss = iss_sim
    self._pcapfile = None
    self._addr = (addr, port)
    if pcap_fname:
      self._pcapfile = pcap.open(pcap_fname, 'w')

    self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  def _run(self):
    while True:
      _data = self._iss.recvTlm()
      if _data:
        if len(_data) > 0:
          self._sock.sendto(_data, self._addr)
          if self._pcapfile:
            self._pcapfile.write(_data)

      gevent.sleep(0)

  def stop(self):
    super(TlmTask, self).kill(block=True, timeout=1)
    self._pcapfile.close()

  def pcap_file(fname):
    if self._pcapfile:
      self._pcapfile.close()

    # Note that sending an empty string or a None will implicitly close the
    # PCAP file.
    if fname and len(fname):
      self._pcapfile = pcap.open(fname, 'w')

class ISSSim (object):
  _epoch_delta = datetime.timedelta()

  def __init__ (self, card=0, rtaddr=6, pcap_fname=None, hnssize=0, tlm_lock_timeout=5,
                tlmaddr="127.0.0.1", tlmport=3076, verbose=True):
    """Creates a new ISS C&DH simulator using the given BTI card number as
    Bus Controller (BC).  Currently, only a single payload is
    supported at the given Remote Terminal (RT) address.

    Start and stop the simulator with start() and stop(), respectively.
    Drive the simulator via step().
    """
    self.verbose = verbose

    if self.verbose:
      log.info("Initializing BTICard(card=%d)." % card)

    self.api    = bti.BTI1553(card)
    # Placing this reset here because the event log example (examp10) does it
    # this early
    self.api.reset()
    self.event  = bti.BTIEvent()
    self.rtaddr = rtaddr

    if self.verbose:
      log.info("Setting up to be a 1553 bus controller.")

    self.api.BCConfig()
    self.api.EventLogConfig(flags=bti.LOGCFG_ENABLE, count=1024)

    self.tlmQ = [ ]
    self.cmdQ = [ ]

    if self.verbose:
      log.info("Allocating ISS PL MDM messages.")

    self.syncMsg = SyncMsg(self.api)
    self.timeMsg = TimeMsg(self.api)
    self.badMsg  = BADMsg (self.api)
    self.cmdMsg  = CmdMsg (self.api, self.rtaddr)
    self.tlmPoll = [ TlmMsg(self.api, self.rtaddr) for n in range(40) ]

    if self.verbose:
      log.info("Installing the ISS C&DH 1553B Schedule.")

    microseconds = int(1e6)
    # There are 10 sub frames per frame
    subframes    = 10
    # The BTI API works in microsecond intervals
    duration     = microseconds / subframes

    if self.verbose:
      log.info("Scheduling messages")

    # The __init__ of most of the messages make calls to BCSchedMsg. This call
    # is here to "reset" the schedule to this point so that we can control what
    # is in each subframe.
    self.api.BCSchedEntry()

    self.pollLen = 0
    if hnssize > 0:
      log.info("Using given H&S packet size %d" % hnssize)
      self.pollLen = TlmPkt.pollsPerPktLen(hnssize)
      log.info('Will need %d polls' % self.pollLen)

    # We will make 10 sub frames at 10ms apart
    for subframe in range(subframes):
      # Each sub frame starts off with a schedule frame call.
      self.api.BCSchedFrame(duration)

      # Schedule the time message on the 3rd sub frame
      if subframe == 2:
        self.timeMsg.schedule(oneshot = 1, skip = 1)

      # Sync message every sub frame
      self.syncMsg.schedule()
      self.sync_count = 0
      # Schedule the first H & S poll of the subframe
      if self.pollLen > 0 and subframe * 4 < self.pollLen:
        """If the sim was initialized with H&S packet length then the first
        poll message of the subframe that is required will be scheduled."""
        self.tlmPoll[ 0 + subframe * 4 ].schedule()
      elif self.pollLen == 0 and subframe == 0:
        """If the number of polls has to be detected then only schedule the
        first poll of the first sub frame."""
        self.tlmPoll[ subframe * 4 ].schedule()
      elif self.pollLen == 0:
        "Mark the other first polls in the sub frames as skip"
        self.tlmPoll[ subframe * 4 ].schedule(oneshot=1, skip=1)

      # Schedule the command message
      self.cmdMsg .schedule(oneshot = 1, skip = 1)
      # Schedule the BAD message
      self.badMsg .schedule(oneshot = 1, skip = 1)

      # There are 4 total H & S telemetry polls in any subframe. We already scheduled
      # one. Now we need to schedule the other three.
      if self.pollLen > 0 and subframe * 4 < self.pollLen:
        for n in range(1, 4):
          if subframe * 4 + n < self.pollLen:
            self.tlmPoll[ n + subframe * 4 ].schedule()
      elif self.pollLen == 0:
        if subframe == 0:
          """Schedule the last three messages in the first sub frame"""
          for n in range(1, 4):
            self.tlmPoll[ n + subframe * 4 ].schedule()
        else:
          """Mark all of the other messages as skipped"""
          for n in range(1, 4):
            self.tlmPoll[ n + subframe * 4 ].schedule(oneshot=1, skip=1)

    self.pollN = 0
    self.bad_pkt = None
    self._svcTlmThr = gevent.Greenlet.spawn(self.runTlm)
    self._sendTlmThr = TlmTask(self, pcap_fname=pcap_fname, addr=tlmaddr, port=tlmport)
    self._sendTlmThr.start()
    self._tlmLostLockCount = 0
    self._tlmLostLockTimeout = tlm_lock_timeout

  def _svcTlm (self):
    """Method to poll telemetry on the 1553 bus. The PL/MDM sim can put out up
    to 40 health and status packets on the bus. The payload then writes into
    those packets. The number of packets is a function of the CCSDS packet
    length. The sim starts by putting out 4 telemetry polls in the first sub
    frame. The payload writes a CCSDS header into the first of those four
    polls. The sim is required to read the header and extract the packet
    length. Once that packet length is known the sim then turns on the required
    number of polls."""
    if self.pollLen == 0:
      """We have to detect the number of polls we have to put out by reading a
      CCSDS header. That header will be in the first poll in the first sub
      frame of every frame."""
      if self.tlmPoll[0].isDataReady() is True:
        """The isDataReady() call looks at the HIT and RESP flags in the error
        bit field. If both are true it means that something both read and wrote
        a response to the packet."""
        self.tlmPoll[0].read()
        tmpPkt = TlmPkt(self.tlmPoll[0].data)
        if tmpPkt.isValid(APID) is True:
          self.pollLen = TlmPkt.pollsPerPktLen(tmpPkt._length + 7)
          log.info('Setting up %d H&S telemetry polls' % self.pollLen)
          for n in range(4, self.pollLen):
            "Mark the pre-generated polls so they will be scheduled on the bus"
            self.tlmPoll[n].oneshot=0
            self.tlmPoll[n].skip=0
          self.putHnS(self.tlmPoll[0].data)
          # Begin our internal index
          self.pollN += 1

        # Clear the packet's error field.
        self.tlmPoll[0].clearErrFld()
    elif self.pollN < self.pollLen:
      """Our internal index is less than the number of polls we should read in
      any H&S polling cycle. This means we have established the payload polling
      size."""
      if self.tlmPoll[self.pollN].isDataReady() is True:
        self.tlmPoll[self.pollN].read()
        self.putHnS(self.tlmPoll[self.pollN].data)
        testPkt = TlmPkt(self.tlmPoll[self.pollN].data)
        if self.pollN == 0 and not testPkt.isValid(APID):
          log.warn('First poll does not have a CCSDS header in it.')
          self._tlmLostLockCount += 1
          if self._tlmLostLockCount > self._tlmLostLockTimeout:
            """ We have lost lock with the payload for more then configured
            timeout (seconds). Attempt to lock again. This means going back to
            only the first 4 polls and marking the poll length as zero."""
            log.warn('Exceeded lost lock timeout: %d seconds. Attempting to restart lock' % self._tlmLostLockTimeout)
            for n in range(4, 40):
              self.tlmPoll[n].oneshot=1
              self.tlmPoll[n].skip=1
            self.pollLen = 0
            self.pollN = 0
            # Reset the telemetry queue
            self.tlmQ = list()
            self._tlmLostLockCount = 0
            return
        elif self.pollN == 0:
          self._tlmLostLockCount = 0

        self.tlmPoll[self.pollN].clearErrFld()
        self.pollN += 1
    else:
      """We have captured all of the available H&S telemetry for this cycle.
      Restart the cycle"""
      self.pollN = 0

  def runTlm(self):
    """Method to pass to a greenlet to run the H&S telemetry polling service"""
    while True:
      self._svcTlm()
      gevent.sleep(0)

  def recvTlm (self):
    """Receives the next segment of ISS payload telemetry or None."""
    pkt = None
    if self.pollLen == 0:
      "The number of polls have not yet been detected."
      return pkt

    if len(self.tlmQ) >= self.pollLen:
      """There is enough data in the queue to assemble a H&S packet"""
      ccsds     = TlmPkt( self.peekHnS() )
      discarded = 0
      """Get from the queue until we find the front of a packet"""
      while ccsds.isValid(APID) is not True:
        discarded += 1
        # Drop this packet.
        self.getHnS()
        if len(self.tlmQ) == 0:
          break
        ccsds = TlmPkt( self.peekHnS() )

      if discarded > 0:
        msg = 'Discarded %d telemetry frame(s) (attempting CCSDS sync)'
        log.warn(msg % discarded)

    if len(self.tlmQ) >= self.pollLen:
      """The above conditional statements should guarantee that the head of the
      queue is the start of a packet. Start assembling that packet"""
      pkt = bytearray()
      for n in range(self.pollLen):
        pkt += self.getHnS()

    return pkt


  def sendCmd (self, cmd):
    """Sends the given command to the ISS payload.  The command may be
    a string or byte array of 106 bytes (53 words).

    The command is queued and will be processed according to its
    position in the queue and the ISS Payload MDM 1553B bus schedule.
    """
    if len(cmd) > 106:
      msg = "Rejecting command, too long (%d bytes > 106 bytes)."
      log.error(msg % len(cmd))
      gds.hexdump(cmd, preamble="Command: ", addr=0)
    else:
      self.cmdQ.insert(0, cmd)
      args = len(cmd), len(self.cmdQ)
      log.debug("Command queued   (bytes=%d, qlen=%d)." % args)


  def start (self):
    """Starts the ISS Payload MDM Simulator."""
    ISSSim.reset_time()
    self.time = datetime.datetime.utcnow() - self._epoch_delta
    self.api.start()

  @classmethod
  def reset_time(cls):
    if session_epoch is not None:
      cls._epoch_delta = datetime.datetime.utcnow() - session_epoch

  def step (self):
    """Steps the ISS Payload MDM Simulator."""
    self.time = datetime.datetime.utcnow() - ISSSim._epoch_delta
    self.event = self.api.EventLogRd(self.event)

    if not self.event.empty:
      self.badMsg.update(self.sync_count % 100, self.time)
      self.sync_count += 1

    if self.timeMsg.isReady():
      nextTime = self.time
      lastTime = self.timeMsg.time
      elapsed  = nextTime - lastTime

      if elapsed.total_seconds() < 1:
        nextTime += datetime.timedelta(seconds=1)

      self.timeMsg.update(nextTime)

    if self.cmdMsg.isReady() and len(self.cmdQ) > 0:
      self.cmdMsg.update(self.time, self.cmdQ.pop())

  def stop (self):
    """Stops the ISS Payload MDM Simulator."""
    self._svcTlmThr.kill(block=True, timeout=1)
    self._sendTlmThr.stop()
    self.api.stop()
    self.api.reset()
    self.api.card.close()

  # The number of polls required to get all of the packet data. Note we have to
  # add one more poll if the number of words per message is odd
  def numPolls(self, pkt):
    adjustpoll = 0
    if pkt.lenInWords() % 32 > 0:
        adjustpoll = 1

    return pkt.lenInWords() / TlmMsg.WordsPerMsg + adjustpoll

  def putHnS(self, data):
    """ The H&S telemetry queue is a list of data, not a queue. This function
    , peek and get hide this fact."""
    self.tlmQ.insert(0, data)

  def peekHnS(self):
    """Peek at the head of the H&S telemetry queue"""
    return self.tlmQ[-1]

  def getHnS(self):
    return self.tlmQ.pop()

  def reset(self):
    """
    Assuming you have one ISSSim object, this will reset the time and BAD
    playback
    """
    BADPkt.reset_time()
    CmdPkt.reset_time()
    TimeMsg.reset_time()
    ISSSim.reset_time()
    global sto_source
    if sto_source is not None:
      sto_source.reset()
