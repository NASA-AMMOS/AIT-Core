"""
Ballard Technology Incorporated (BTI) API

The BTI module provides APIs for Ballard 1553 and RS-422 devices (e.g.
USB adapters and PCI cards) on Windows and Linux by exposing both
Ballard's C functions and a Pythonic object-oriented interface.

The module loads the BTI DLLs (Windows) or shared object libraries
(Linux) and communicates with them via Python's foreign function
interface package, ctypes.

Ballard's C API function names begin with "BTI1553_" or "BTICard_".
Only function names in the list bti.FunctionNames may be called.  The
Pythonic interface offers BTICard and BTI1553 objects which maintain
the card, core, and channel state internally and raise BTIError
exceptions on error.

For example, to use the C API directly to open card zero:

  >>> hcard  = bti.HCARD()
  >>> errval = bti.BTICard_CardOpen(ctypes.byref(hcard), 0)

The same can be accomplished by creating a BTICard:

  >>> card = BTICard(0)

Note that the former requires errval to be checked for an error,
whereas the latter will raise BTIError exceptions, e.g.:

  bti.BTIError: -13=ERR_NOCARD CardOpen() could not find a BTICard
  device at the s pecified address (BTICard)

The following implements BTI example Bus Controller EXAMP1.C using the
BTI Python API:


  import bti

  bus  = bti.BTI1553(card=0)
  data = (0xCAFE, 0xD00D)
  msg  = bti.XmitFields1553(taddr=1, rtxmit=0, saddr=2, data=data)

  bus.BCConfig()
  bus.BCSchedFrame(1000)
  bus.start()

  try:
    print "BC is running (Ctrl-C to exit)."
    print "  Sending: %s" % ", ".join([ "0x%04X" % d for d in data ])
    while True:
      bus.BCTransmitMsg(msg)

      if msg.errors.isANYERR:
        print msg.errors
  except KeyboardInterrupt:
    print "done."
    bus.stop()
    bus.card.close()


And similarly, the Remote Terminal from EXAMP3.C:


  import bti
  import ctypes

  bus = bti.BTI1553(card=1)
  bus.RTConfig(taddr=1)

  msg  = bus.RTGetMsg(0, 1, 0, 2)
  data = (ctypes.c_uint16 * 2)()  # Allocate two 16-bit data words.
  bus.start()

  try:
    while True:
      bus.MsgDataRd(data, msg)
      print "Recv: 0x%04X, 0x%04X (Ctrl-C to exit)." % (data[0], data[1])
  except KeyboardInterrupt:
    print "done."
    bus.stop()
    bus.card.close()
"""


"""
Authors: Ben Bornstein

Copyright 2013 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""


import ctypes


# Export each function in FunctionNames into this module's namespace.
FunctionNames = [
  "BTI1553_BCConfig"        ,
  "BTI1553_BCConfigEx"      ,
  "BTI1553_BCCreateList"    ,
  "BTI1553_BCCreateMsg"     ,
  "BTI1553_BCSchedCall"     ,
  "BTI1553_BCSchedEntry"    ,
  "BTI1553_BCSchedFrame"    ,
  "BTI1553_BCSchedGap"      ,
  "BTI1553_BCSchedLog"      ,
  "BTI1553_BCSchedMsg"      ,
  "BTI1553_BCSchedRestart"  ,
  "BTI1553_BCSchedReturn"   ,
  "BTI1553_BCTransmitMsg"   ,
  "BTI1553_ChIs1553"        ,
  "BTI1553_CmdShotRd"       ,
  "BTI1553_CmdShotWr"       ,
  "BTI1553_CmdSkipRd"       ,
  "BTI1553_CmdSkipWr"       ,
  "BTI1553_ListDataRd"      ,
  "BTI1553_ListDataWr"      ,
  "BTI1553_ListMultiBlockWr",
  "BTI1553_ListStatus"      ,
  "BTI1553_MonConfig"       ,
  "BTI1553_MsgCommRd"       ,
  "BTI1553_MsgCommWr"       ,
  "BTI1553_MsgDataRd"       ,
  "BTI1553_MsgDataWr"       ,
  "BTI1553_MsgFieldRd"      ,
  "BTI1553_MsgFieldWr"      ,
  "BTI1553_RTConfig"        ,
  "BTI1553_RTGetMsg"        ,
  "BTI1553_ValPackCWD"      ,
  "BTI1553_ValUnpackCWD"    ,
  "BTI422_FIFODataRd"       ,
  "BTI422_FIFODataWr"       ,
  "BTI422_FIFOFlushRx"      ,
  "BTI422_FIFOFlushTx"      ,
  "BTI422_PortConfig"       ,
  "BTI422_PortGetCount"     ,
  "BTI422_PortIs422"        ,
  "BTICard_CardClose"       ,
  "BTICard_CardOpen"        ,
  "BTICard_CardProductStr"  ,
  "BTICard_CardReset"       ,
  "BTICard_CardStart"       ,
  "BTICard_CardStop"        ,
  "BTICard_CardTypeStr"     ,
  "BTICard_CoreOpen"        ,
  "BTICard_ErrDescStr"      ,
  "BTICard_EventLogConfig"  ,
  "BTICard_EventLogRd"      ,
  "BTICard_SeqBlkRd"            ,
  "BTICard_SeqConfig"           ,
  "BTICard_SeqFindCheckVersion" ,
  "BTICard_SeqFindInit"         ,
  "BTICard_SeqFindMore1553"     ,
  "BTICard_SeqFindNext1553"
]

LibBTICard  = None
LibBTI1553  = None
LibBTI422   = None
LibBTIError = None

try:
  if hasattr(ctypes, 'windll'):
    LibBTICard = ctypes.windll.LoadLibrary("BTICARD.DLL")
    LibBTI1553 = ctypes.windll.LoadLibrary("BTI1553.DLL")
    LibBTI422  = ctypes.windll.LoadLibrary("BTI422.DLL")
  else:
    LibBTICard = ctypes.cdll.LoadLibrary("libbtiCard.so")
    LibBTI1553 = ctypes.cdll.LoadLibrary("libbti1553.so")
    LibBTI422  = ctypes.cdll.LoadLibrary("libbti422.so")

  _namespace = globals()

  for _name in FunctionNames:
    _libname          = _name.split("_")[0]
    _lib              = _namespace["Lib" + _libname]
    _namespace[_name] = _lib[_name]

  BTICard_CardProductStr.restype = ctypes.c_char_p
  BTICard_CardTypeStr.restype    = ctypes.c_char_p
  BTICard_ErrDescStr.restype     = ctypes.c_char_p
except OSError as e:
  LibBTIError = e


HCARD    = ctypes.c_voidp
HCORE    = ctypes.c_voidp
LISTADDR = ctypes.c_uint
MSGADDR  = ctypes.c_uint
WORD     = ctypes.c_uint16
MSGDATA  = WORD * 32


#
#  Condition flags
#
COND1553_ALWAYS          = 0x00000000L
COND1553_FAIL            = 0x00000001L
COND1553_SRQ             = 0x00000002L
COND1553_INS             = 0x00000004L
COND1553_SSF             = 0x00000008L
COND1553_TF              = 0x00000010L
COND1553_BUSY            = 0x00000020L
COND1553_ME              = 0x00000040L
COND1553_RESPERR         = 0x00000080L
COND1553_NORESP          = 0x00000100L
COND1553_ALTBUS          = 0x00000200L
COND1553_DIO1ACT         = 0x00001000L
COND1553_DIO1NACT        = 0x00002000L
COND1553_DIO2ACT         = 0x00004000L
COND1553_DIO2NACT        = 0x00008000L
COND1553_DIO3ACT         = 0x00010000L
COND1553_DIO3NACT        = 0x00020000L
COND1553_DIO4ACT         = 0x00040000L
COND1553_DIO4NACT        = 0x00080000L


#
# BC Configuration Flags
#
BCCFG1553_DEFAULT        = 0x00000000L
BCCFG1553_ENABLE         = 0x00000000L
BCCFG1553_DISABLE        = 0x00000001L
BCCFG1553_TRIGNONE       = 0x00000000L
BCCFG1553_TRIGEXT        = 0x00000010L
BCCFG1553_TRIGSTART      = 0x00000020L
BCCFG1553_NOLOGHALT      = 0x00000000L
BCCFG1553_LOGHALT        = 0x00000100L
BCCFG1553_NOLOGPAUSE     = 0x00000000L
BCCFG1553_LOGPAUSE       = 0x00000200L
BCCFG1553_NOLOOPMAX      = 0x00000000L
BCCFG1553_LOOPMAX        = 0x00001000L
BCCFG1553_NOSTEP         = 0x00000000L
BCCFG1553_STEP           = 0x00002000L
BCCFG1553_MC01           = 0x00000000L
BCCFG1553_MC1            = 0x01000000L
BCCFG1553_MC0            = 0x02000000L
BCCFG1553_MCNONE         = 0x03000000L
BCCFG1553_TERMOFF        = 0x00000000L
BCCFG1553_TERMONA        = 0x04000000L
BCCFG1553_TERMONB        = 0x08000000L
BCCFG1553_TERMONAB       = 0x0C000000L
BCCFG1553_SYNCSEL        = 0x00000000L
BCCFG1553_SYNCALL        = 0x40000000L
BCCFG1553_PAUSE          = 0x00000400L
BCCFG1553_UNPAUSE        = 0x00000000L
BCCFG1553_SELFTEST       = 0x00800000L
BCCFG1553_SELFTESTOFF    = 0x00000000L


#
# Event types
#
EVENTTYPE_1553MSG        = 0x0001
EVENTTYPE_1553OPCODE     = 0x0002
EVENTTYPE_1553HALT       = 0x0003
EVENTTYPE_1553PAUSE      = 0x0004
EVENTTYPE_1553LIST       = 0x0005
EVENTTYPE_1553SERIAL     = 0x0006
EVENTTYPE_429MSG         = 0x0011
EVENTTYPE_429OPCODE      = 0x0012
EVENTTYPE_429HALT        = 0x0013
EVENTTYPE_429PAUSE       = 0x0014
EVENTTYPE_429LIST        = 0x0015
EVENTTYPE_429ERR         = 0x0016
EVENTTYPE_717WORD        = 0x0021
EVENTTYPE_717SUBFRM      = 0x0022
EVENTTYPE_717SYNCERR     = 0x0023
EVENTTYPE_708MSG         = 0x0031
EVENTTYPE_SEQFULL        = 0x0041
EVENTTYPE_SEQFREQ        = 0x0042
EVENTTYPE_422TXTHRESHOLD = 0x0051
EVENTTYPE_422TXFIFO      = 0x0052
EVENTTYPE_422RXTHRESHOLD = 0x0053
EVENTTYPE_422RXFIFO      = 0x0054
EVENTTYPE_422RXERROR     = 0x0055
EVENTTYPE_CSDBMSG        = 0x0058
EVENTTYPE_CSDBOPCODE     = 0x0059
EVENTTYPE_CSDBHALT       = 0x005A
EVENTTYPE_CSDBPAUSE      = 0x005B
EVENTTYPE_CSDBLIST       = 0x005C
EVENTTYPE_CSDBERR        = 0x005D
EVENTTYPE_CSDBSYNCERR    = 0x005E
EVENTTYPE_DIOEDGE        = 0x0060
EVENTTYPE_DIOFAULT       = 0x0061
EVENTTYPE_BITERROR       = 0x0071


#
#  Field types
#
FIELD1553_CWD1           = 0x0000
FIELD1553_CWD2           = 0x0001
FIELD1553_SWD1           = 0x0002
FIELD1553_SWD2           = 0x0003
FIELD1553_TTAG           = 0x0004
FIELD1553_ELAPSE         = 0x0005
FIELD1553_ERROR          = 0x0006
FIELD1553_ACT            = 0x0007
FIELD1553_RESP1          = 0x0008
FIELD1553_RESP2          = 0x0009
FIELD1553_COUNT          = 0x000A
FIELD1553_FLAG1          = 0x000B
FIELD1553_FLAG2          = 0x000C
FIELD1553_EXTFLAG        = 0x000D
FIELD1553_TTAGH          = 0x000E


#
#  List buffer options
#
LISTCRT1553_DEFAULT      = 0x00000000L
LISTCRT1553_PINGPONG     = 0x00000000L
LISTCRT1553_FIFO         = 0x00000001L
LISTCRT1553_CIRCULAR     = 0x00000002L
LISTCRT1553_TRBIT        = 0x00000000L
LISTCRT1553_READ         = 0x00000010L
LISTCRT1553_WRITE        = 0x00000020L
LISTCRT1553_NOTSKIP      = 0x00000000L
LISTCRT1553_SKIP         = 0x00000040L
LISTCRT1553_ASYNC        = 0x00000080L
LISTCRT1553_NOLOG        = 0x00000000L
LISTCRT1553_LOG          = 0x00000100L
LISTCRT1553_NOHIT        = 0x00000000L
LISTCRT1553_HIT          = 0x00000200L
LISTCRT1553_NOLOGHALF    = 0x00000000L
LISTCRT1553_LOGHALF      = 0x00000400L


#
# Event log list configuration options
#
LOGCFG_DEFAULT           = 0x00000000L
LOGCFG_ENABLE            = 0x00000000L
LOGCFG_DISABLE           = 0x00000001L

#
# Bit fields of the message activity flag
#
MSGACT1553_CHMASK      = 0xF000 # number mask value
MSGACT1553_CHSHIFT     = 0x000C # number shift value
MSGACT1553_XMTCWD1     = 0x0800 # CWD1
MSGACT1553_XMTCWD2     = 0x0400 # CWD2
MSGACT1553_XMTSWD1     = 0x0200 # SWD1
MSGACT1553_XMTSWD2     = 0x0100 # SWD2
MSGACT1553_RCVCWD1     = 0x0080 # CWD1
MSGACT1553_RCVCWD2     = 0x0040 # CWD2
MSGACT1553_RCVSWD1     = 0x0020 # SWD1
MSGACT1553_RCVSWD2     = 0x0010 # SWD2
MSGACT1553_XMTDWD      = 0x0008 # DWD
MSGACT1553_RCVDWD      = 0x0004 # DWD

#
# Message Configuration Options
#
MSGCRT1553_DEFAULT       = 0x00000000L
MSGCRT1553_ENABLE        = 0x00000000L
MSGCRT1553_DISABLE       = 0x00001000L
MSGCRT1553_RESP          = 0x00000000L
MSGCRT1553_NORESP        = 0x00002000L
MSGCRT1553_NOWRAP        = 0x00000000L
MSGCRT1553_WRAP          = 0x00004000L
MSGCRT1553_NOLOG         = 0x00000000L
MSGCRT1553_LOG           = 0x00000001L
MSGCRT1553_NOERR         = 0x00000000L
MSGCRT1553_ERR           = 0x00000002L
MSGCRT1553_BUSA          = 0x00000000L
MSGCRT1553_BUSB          = 0x00000004L
MSGCRT1553_BCRT          = 0x00000000L
MSGCRT1553_RTRT          = 0x00000008L
MSGCRT1553_NOMON         = 0x00000000L
MSGCRT1553_MON           = 0x00000010L
MSGCRT1553_NOTIMETAG     = 0x00000000L
MSGCRT1553_TIMETAG       = 0x00000040L
MSGCRT1553_NOELAPSE      = 0x00000000L
MSGCRT1553_ELAPSE        = 0x00000080L
MSGCRT1553_NOMIN         = 0x00000000L
MSGCRT1553_MIN           = 0x00000100L
MSGCRT1553_NOMAX         = 0x00000000L
MSGCRT1553_MAX           = 0x00000200L
MSGCRT1553_NOHIT         = 0x00000000L
MSGCRT1553_HIT           = 0x00000400L
MSGCRT1553_NOSYNC        = 0x00000000L
MSGCRT1553_SYNC          = 0x40000000L
MSGCRT1553_WIPE          = 0x00000000L
MSGCRT1553_NOWIPE        = 0x80000000L
MSGCRT1553_WIPE0         = 0x00000000L
MSGCRT1553_WIPE123       = 0x01000000L
MSGCRT1553_WIPECWD       = 0x02000000L


#
# Bit fields of the message error flag
#
MSGERR1553_NORESP        = 0x8000
MSGERR1553_ANYERR        = 0x4000
MSGERR1553_PROTOCOL      = 0x2000
MSGERR1553_SYNC          = 0x1000
MSGERR1553_DATACOUNT     = 0x0800
MSGERR1553_MANCH         = 0x0020
MSGERR1553_PARITY        = 0x0010
MSGERR1553_WORD          = 0x0008
MSGERR1553_RETRY         = 0x0004
MSGERR1553_SYSTEM        = 0x0002
MSGERR1553_HIT           = 0x0001

#
# Remote terminal configuration options
#
RTCFG1553_DEFAULT        = 0x00000000L
RTCFG1553_SIMULATE       = 0x00000000L
RTCFG1553_DISABLE        = 0x00000001L
RTCFG1553_MONITOR        = 0x00000002L
RTCFG1553_NOBCAST        = 0x00000000L
RTCFG1553_BCAST          = 0x00000100L
RTCFG1553_NOAUTOBUSY     = 0x00000000L
RTCFG1553_AUTOBUSY       = 0x00000200L
RTCFG1553_BUILD          = 0x00000000L
RTCFG1553_NOBUILD        = 0x00000400L
RTCFG1553_STDB           = 0x00000000L
RTCFG1553_STDA           = 0x00400000L
RTCFG1553_NODYNBC        = 0x00000000L
RTCFG1553_DYNBC          = 0x00001000L
RTCFG1553_NOIMMCLR       = 0x00000000L
RTCFG1553_IMMCLR         = 0x00002000L
RTCFG1553_NOBCASTADDR    = 0x00000000L
RTCFG1553_BCASTADDR      = 0x00004000L
RTCFG1553_CHANAB         = 0x00000000L
RTCFG1553_CHANA          = 0x00020000L
RTCFG1553_CHANB          = 0x00010000L
RTCFG1553_CHANNONE       = 0x00030000L
RTCFG1553_MC01           = 0x00000000L
RTCFG1553_MC1            = 0x01000000L
RTCFG1553_MC0            = 0x02000000L
RTCFG1553_MCNONE         = 0x03000000L
RTCFG1553_TERMOFF        = 0x00000000L
RTCFG1553_TERMONA        = 0x04000000L
RTCFG1553_TERMONB        = 0x08000000L
RTCFG1553_TERMONAB       = 0x0C000000L
RTCFG1553_SYNCSEL        = 0x00000000L
RTCFG1553_SYNCALL        = 0x40000000L
RTCFG1553_WIPE           = 0x00000000L
RTCFG1553_NOWIPE         = 0x80000000L
RTCFG1553_WIPE0          = 0x00000000L
RTCFG1553_WIPE123        = 0x10000000L
RTCFG1553_WIPECWD        = 0x20000000L
RTCFG1553_RESPONSEB      = 0x00000000L
RTCFG1553_RESPONSEA      = 0x00400000L
RTCFG1553_SELFTEST       = 0x00800000L
RTCFG1553_SELFTESTOFF    = 0x00000000L

#
# Monitor configuration options
#
MONCFG1553_DEFAULT     = 0x00000000L
MONCFG1553_ENABLE      = 0x00000000L
MONCFG1553_DISABLE     = 0x00000001L
MONCFG1553_NOBCAST     = 0x00000000L
MONCFG1553_BCAST       = 0x00000100L
MONCFG1553_COMPLETE    = 0x00000000L
MONCFG1553_INCOMPLETE  = 0x00010000L
MONCFG1553_MC01        = 0x00000000L
MONCFG1553_MC1         = 0x00100000L
MONCFG1553_MC0         = 0x00200000L
MONCFG1553_MCNONE      = 0x00300000L
MONCFG1553_TERMOFF     = 0x00000000L
MONCFG1553_TERMONA     = 0x04000000L
MONCFG1553_TERMONB     = 0x08000000L
MONCFG1553_TERMONAB    = 0x0C000000L
MONCFG1553_SELFTEST    = 0x00800000L
MONCFG1553_SELFTESTOFF = 0x00000000L

#
# Record configuration options
#
SEQCFG_DEFAULT     = 0x00000000L
SEQCFG_FILLHALT    = 0x00000000L
SEQCFG_DISABLE     = 0x00000001L
SEQCFG_CONTINUOUS  = 0x00000002L
SEQCFG_DMA         = 0x00000004L
SEQCFG_FREE        = 0x00000008L
SEQCFG_DELTA       = 0x00000010L
SEQCFG_INTERVAL    = 0x00000020L
SEQCFG_NOLOGFULL   = 0x00000000L
SEQCFG_LOGFULL     = 0x00001000L
SEQCFG_NOLOGFREQ   = 0x00000000L
SEQCFG_LOGFREQ     = 0x00002000L
SEQCFG_16K         = 0x00000000L
SEQCFG_ALLAVAIL    = 0x01000000L
SEQCFG_32K         = 0x02000000L
SEQCFG_64K         = 0x04000000L
SEQCFG_128K        = 0x08000000L

SEQVER_MASK = 0xff00
SEQVER_0    = 0x0000
SEQVER_1    = 0x0100

#
# Status flags
#
STAT_EMPTY               = 0
STAT_PARTIAL             = 1
STAT_FULL                = 2
STAT_OFF                 = 3

#
# Other flags
#
SUBADDRESS = 0x0000 # Selects sub-address messages
MODECODE   = 0x0001 # Selects mode code messages


def checkLibLoaded ():
  """Raises an exception if the BTI libraries were loaded."""
  if LibBTIError:
    msg = "The BTI libraries could not be loaded: " + str(LibBTIError)
    raise ImportError(msg)


def sizeof_words (data):
  """Returns the sizeof data in 16-bit words, instead of bytes."""
  return ctypes.sizeof(data) / ctypes.sizeof(ctypes.c_uint16)


class BTI1553 (object):
  def __init__ (self, card=0, core=0, channel=0):
    """Creates a new BTI1553 device with the given card, core, and channel
    numbers. The BTI driver supports multiple users of the same card, but
    this module does not. Please specify what card, core and channel instance
    numbers you want to use.
    """
    checkLibLoaded()
    super(BTI1553, self).__init__()
    self._card    = None
    self._channel = None
    self._core    = None
    self._hcore   = HCORE(0)
    self._product = None
    self._type    = None

    if type(card) is int:
      self._card = BTICard(card)
    elif isinstance(card, BTICard):
      self._card = card
    else:
      raise TypeError("Card must be an integer or BTICard.")

    if self.open(core, channel) is 0:
      self.reset()
      self._product = BTICard_CardProductStr(self._hcore)
      self._type    = BTICard_CardTypeStr(self._hcore)


  def __open__ (self, core=0, channel=0):
    """Opens the given BTI 1553 core and channel."""
    errval = BTICard_CoreOpen(ctypes.byref(self._hcore), core, self.card)
    if errval is 0:
      self._core = core
      errval     = self.__set_channel__(channel)
      if errval is not 0:
        self.close()

    return errval


  def __repr__ (self):
    return "BTI1553(card=%s, core=%s)" % (str(self.card), str(self.core))


  def __set_channel__ (self, channel=-1):
    """Sets the current 1553 channel."""
    errval = 0
    if channel >= 0:
      if BTI1553_ChIs1553(channel, self._hcore):
        self._channel = channel
      else:
        # ERR_NOTCHAN The specified channel is invalid (BTICard)
        errval = -23
    else:
      for channel in range(0, BTICard.MAX_CHANNELS):
        errval = self.__set_channel__(channel)
        if errval is 0:
          break

    return errval


  @property
  def _as_parameter_ (self):
    """The underlying BTI core handle."""
    return self._hcore


  @property
  def card (self):
    """The BTICard."""
    return self._card


  @property
  def channel (self):
    """The current 1553 channel."""
    return self._channel


  @property
  def core (self):
    """The BTI core number."""
    return self._core


  @property
  def product (self):
    """Product information for the underlying BTI device core."""
    return self._product


  @property
  def type (self):
    """Type information for the underlying BTI device core."""
    return self._type


  @channel.setter
  def channel (self, channel):
    """Sets the current 1553 channel (if valid)."""
    errval = self.__set_channel__(channel)
    BTIError.raise_if(errval, self.card)


  def open (self, core=-1, channel=-1):
    """Opens the given BTI 1553 core and channel.  If not given, cores
    and/or channels on the current card are scanned and the first 1553
    channel found is opened.
    """
    errval = self.__open__(core, channel)
    return BTIError.raise_if(errval, self.card)


  def reset (self):
    """Resets the current BTI 1553 core."""
    errval = BTICard_CardReset(self._hcore)
    return BTIError.raise_if(errval, self.card)


  def start (self):
    """Starts the current BTI 1553 core."""
    errval = BTICard_CardStart(self._hcore)
    return BTIError.raise_if(errval, self.card)


  def stop (self):
    """Stops the current BTI 1553 core."""
    errval = BTICard_CardStop(self._hcore)
    if errval is 0:
      self._core        = None
      self._hcore.value = 0
    return BTIError.raise_if(errval, self.card)

  def monitor(self):
    """Monitor the 1553 bus. Used as an iterator (like readline()), it yields a
    sequence monitor packet. This function currently requires a bunch of stuff
    to happen first. Specifically, it requires MonConfig(), SeqConfig() and
    start() to be called prior to it being called. The function will return a
    tuple of a 1553 sequence record and sequence more record. That record
    includes the 1553 packet."""
    seqbuf = (ctypes.c_uint16 * 2048)()
    blkcnt = ctypes.c_uint32(0)
    pRec1553 = ctypes.POINTER(SEQRECORD1553)()
    pRecMore1553 = ctypes.POINTER(SEQRECORDMORE1553)()
    # Enter loop, we'll depend on the caller to break.
    while True:
      # Copy any sequential records to seqbuf
      seqcount = BTICard_SeqBlkRd(seqbuf, len(seqbuf),
                                  ctypes.byref(blkcnt), self._hcore)

      sfinfo = SEQFINDINFO()
      # Initialize the sequence list walking
      errval = BTICard_SeqFindInit(seqbuf, seqcount, ctypes.byref(sfinfo))
      if errval:
        BTIError.raise_if(errval, self.card)
        return

      # Walk the list of sequential records until it is empty
      while BTICard_SeqFindNext1553(ctypes.byref(pRec1553), ctypes.byref(sfinfo)) == 0:
        if BTICard_SeqFindCheckVersion(pRec1553, SEQVER_1):
          if BTICard_SeqFindMore1553(ctypes.byref(pRecMore1553), pRec1553) == 0:
            yield (pRec1553[0], pRecMore1553[0])
          else:
            yield (pRec1553[0], None)
        else:
          yield (pRec1553[0], None)

  def BCConfig (self, flags=BCCFG1553_DEFAULT, count=512):
    """Configures a Bus Controller (BC) for the specified channel with
    the options defined by flags.  The count parameter is used to
    specify the number of BC schedule entries to allocate for the
    schedule (default 512).
    """
    errval = BTI1553_BCConfigEx(flags, count, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def BCCreateList (self, count, flags=LISTCRT1553_DEFAULT,
                    msgflags=MSGCRT1553_DEFAULT, cwd1=0, cwd2=0, data=None):
    """Creates and initializes a message list buffer for the BC, similar
    to BCCreateMsg() except it creates a list buffer. This function
    allocates memory for a list of message structures and initializes
    each entry with the command and data words provided. If data is
    not given or None, data initialization is skipped.

    Returns the address of the list buffer if successful, or raises a
    BTIError.
    """
    if isinstance(cwd1, list) or isinstance(cwd1, tuple):
      cwd1 = BTI1553_ValPackCWD(cwd1[0], cwd1[1], cwd1[2], cwd1[3])

    if isinstance(cwd2, list) or isinstance(cwd2, tuple):
      cwd2 = BTI1553_ValPackCWD(cwd2[0], cwd2[1], cwd2[2], cwd2[3])

    if data is None:
      data = 0
    else:
      data = ctypes.byref(data)

    core = self._hcore
    addr = BTI1553_BCCreateList(flags, count, msgflags, cwd1, cwd2, data, core)

    if addr is 0:
      raise BTIError()
    else:
      return addr


  def BCCreateMsg (self, flags=MSGCRT1553_DEFAULT, cwd1=0, cwd2=0, data=None):
    """Allocates memory for a BC message structure and initializes that
    structure with the command and data words provided.  If data is not given
    or None, data initialization is skipped.

    Returns the address of the message structure if successful, or
    raises a BTIError.
    """
    if isinstance(cwd1, list) or isinstance(cwd1, tuple):
      cwd1 = BTI1553_ValPackCWD(cwd1[0], cwd1[1], cwd1[2], cwd1[3])

    if isinstance(cwd2, list) or isinstance(cwd2, tuple):
      cwd2 = BTI1553_ValPackCWD(cwd2[0], cwd2[1], cwd2[2], cwd2[3])

    if data is None:
      data = 0
    else:
      data = ctypes.byref(data)

    addr = BTI1553_BCCreateMsg(flags, cwd1, cwd2, data, self._hcore)

    if addr is 0:
      raise BTIError()
    else:
      return addr


  def BCSchedCall (self, condition, index):
    """Inserts a call opcode into the BC schedule. The destination of
    the call is specified by index, and the conditions of the call are
    specified by condition. To return from the call, use
    BTI1553_BCSchedReturn.

    Returns the Schedule index of the newly created BC schedule entry,
    or a negative value if an error occurs.
    """
    schndx = BTI1553_BCSchedCall(condition, index, self._channel, self._hcore)
    return BTIError.raise_if(schndx, self.card)


  def BCSchedEntry (self):
    """Resets the entry point of the BC Schedule to the current
    location. Note that this is not needed by default since the BC
    schedule entry point is automatically set to the first opcode
    scheduled.

    Returns the schedule index of the newly created BC schedule entry,
    or a negative value if an error occurred.
    """
    schndx = BTI1553_BCSchedEntry(self._channel, self._hcore)
    return BTIError.raise_if(schndx, self.card)


  def BCSchedFrame (self, duration):
    """Schedules a BC frame for the given duration in microseconds.
    """
    errval = BTI1553_BCSchedFrame(duration, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def BCSchedGap (self, gapval):
    """
    Schedules a BC gap of gapval * 100ns. The gapval can be between
    40 and 8191 inclusively. Use to control the gaps between messages.
    """
    errval = BTI1553_BCSchedGap(gapval, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def BCSchedLog (self, condition, tagval):
    """Appends a conditional LOG Command Block to the current end of
    the Schedule. A conditional LOG Command Block causes the core to
    generate an Event Log List entry if condition evaluates as
    TRUE.

    Returns the Schedule index of the newly created BC schedule entry,
    or raises a BTIError.
    """
    schndx = BTI1553_BCSchedLog(condition, tagval, self._channel, self._hcore)
    return BTIError.raise_if(schndx, self.card)


  def BCSchedMsg (self, msgaddr):
    """Appends a MESSAGE Command Block to the current end of the
    Schedule. When a MESSAGE Command Block is encountered in the
    Schedule, the message or the next message from the associated list
    specified by message is transmitted.

    Returns the Schedule index of the newly created BC schedule entry,
    or raises a BTIError.
    """
    schndx = BTI1553_BCSchedMsg(msgaddr, self._channel, self._hcore)
    return BTIError.raise_if(schndx, self.card)


  def BCSchedRestart (self):
    """Inserts a RESTART opcode into the BC schedule. When this opcode
    is executed, the schedule will continue execution at the schedule
    entry point.

    Note that the BC is automatically configured to restart the
    schedule by default. To deviate from this it is necessary to
    schedule a HALT opcode by using BCSchedHalt().

    Returns the schedule index of the newly created BC schedule entry,
    or a negative value if an error occurred.
    """
    schndx = BTI1553_BCSchedRestart(self._channel, self._hcore)
    return BTIError.raise_if(schndx, self.card)


  def BCSchedReturn (self):
    """Inserts a RETURN opcode into the BC schedule. A RETURN opcode
    returns from a previous CALL opcode and continues BC schedule
    execution after the previous call.

    Returns the schedule index of the newly created BC schedule entry,
    or a negative value if an error occurred.
    """
    schndx = BTI1553_BCSchedReturn(self._channel, self._hcore)
    return BTIError.raise_if(schndx, self.card)


  def BCTransmitMsg (self, msg):
    """Transmits a single message (msg) one time.  The message is
    transmitted at the end of a frame in the schedule.
    """
    errval = \
      BTI1553_BCTransmitMsg(ctypes.byref(msg), self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def CmdShotRd (self, index):
    """Reads the value of the single-shot bit for the BC Schedule
    opcode specified by index.

    Returns TRUE if the single-shot bit is set, otherwise FALSE if not
    set.
    """
    return BTI1553_CmdShotRd(index, self._channel, self._hcore)


  def CmdShotWr (self, value, index):
    """Sets the single-shot bit to value for the schedule entry
    specified by index. When set to TRUE, the single-shot bit
    instructs the BC schedule to process the specified opcode one
    time, and then to set the skip bit after processing is
    complete. The single-shot bit is FALSE (disabled) by default.

    Returns a negative value if an error occurs, or zero if
    successful.
    """
    errval = BTI1553_CmdShotWr(value, index, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def CmdSkipRd (self, index):
    """Reads the value of the skip bit for the BC Schedule opcode
    specified by index.

    Returns TRUE if the skip bit is set, otherwise FALSE if not set.
    """
    return BTI1553_CmdSkipRd(index, self._channel, self._hcore)


  def CmdSkipWr (self, value, index):
    """Sets the skip bit to value for the schedule entry specified by
    index. When set to TRUE, the skip bit instructs the BC schedule to
    skip over processing the specified opcode. The skip bit is FALSE
    (disabled) by default.

    Returns a negative value if an error occurs, or zero if
    successful.
    """
    errval = BTI1553_CmdSkipWr(value, index, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def EventLogConfig (self, flags=LOGCFG_DEFAULT, count=256):
    """Configures and enables the Event Log List of the core specified by
    hCore. The maximum number of entries that may be contained in the
    Event Log List is set by count.
    """
    errval = BTICard_EventLogConfig(flags, count, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def EventLogRd (self, event=None):
    """Reads the next entry from the Event Log List and advances the
    pointer.  If an existing event is passed in, it will be (re)used
    by filling it with the new event information and returning it,
    otherwise a new BTIEvent is created.

    Returns the next event in the Event Log List as a BTIEvent.  If
    the Event Log List is empty, event.empty will be True.
    """
    if event is None:
      event = BTIEvent()

    refs        = map(ctypes.byref, event.c_values)
    result      = BTICard_EventLogRd(refs[0], refs[1], refs[2], self._hcore)
    event.hcore = self._hcore
    event.empty = result is 0

    return event


  def ListDataRd (self, buf, listaddr, count=None):
    """Reads the next data associated with a list buffer, similar to
    MsgDataRd().  This function copies count number of data words to
    buf from the message structure in the list buffer specified by
    listaddr.  If count is not given, it is calculated based on the
    size of buf.

    The number of data words read from the list buffer, or zero if an
    error occurred or unable to read from the list.
    """
    if count is None:
      count = sizeof_words(buf)

    bufp = ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint16))

    return BTI1553_ListDataRd(bufp, count, listaddr, self._hcore)


  def ListDataWr (self, buf, listaddr, count=None):
    """Writes the next data associated with a list buffer, similar to
    MsgDataWr().  This function copies count data words from buf to the
    message structure in the list buffer specified by listaddr.  If
    count is not given, it is calculated based on the size of buf.

    The number of data words written to the list buffer, or zero if
    an error occurred or unable to write to the list.
    """
    if count is None:
      count = sizeof_words(buf)

    bufp = ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint16))

    return BTI1553_ListDataWr(bufp, count, listaddr, self._hcore)


  def ListMultiBlockWr (self, msgs, listaddr):
    """Writes multiple message structures to a list buffer. Similar to
    ListBlockWr() except it writes multiple message structures to the
    list buffer instead of just one.  The parameter listaddr is the
    value returned when the list was created using BCCreateList() or
    RTCreateList().

    Return a non-zero value if the function succeeded, or zero if
    unable to read the list buffer.
    """
    buf = ctypes.byref(msgs)
    return BTI1553_ListMultiBlockWr(buf, len(msgs), listaddr, self._hcore)


  def ListStatus (self, listaddr):
    """Checks the status of the List buffer list, without removing an
    entry. The status value can be tested using the predefined
    constants STAT_EMPTY, STAT_PARTIAL, STAT_FULL, and STAT_OFF.

    Return the status value of the List buffer.
    """
    return BTI1553_ListStatus(listaddr, self._hcore)


  def MsgCommRd (self, msg, msgaddr):
    """Reads an entire message structure at msgaddr from the core into
    msg.  This is similar to MsgBlockRd() or MsgDataRd(), except it
    uses non-contended accesses of Device memory.

    Returns the address of the message structure that was read.
    """
    return BTI1553_MsgCommRd(ctypes.byref(msg), msgaddr, self._hcore)


  def MsgCommWr (self, msg, msgaddr):
    """Writes an entire message structure from msg to msgaddr in the core.
    This is similar to MsgBlockWr() or MsgDataWr(), except it uses
    non-contended accesses of Device memory.

    This method is used to modify certain fields in a message
    structure after it has been read using MsgCommRd(). The user can
    clear the hit bit (msgerr), time-tag, hit count, elapsetime,
    mintime, and maxtime fields and update the cwd1, cwd2, and data
    fields.  All other fields should be restored to the value read.

    Returns the address of the message structure that was written.
    """
    return BTI1553_MsgCommWr(ctypes.byref(msg), msgaddr, self._hcore)


  def MsgDataRd (self, buf, msgaddr, count=None):
    """Reads the data associated with the given message. This function
    copies count data words to buf from the message structure
    specified by msgaddr.  If count is not given, it is calculated
    based on the size of buf.
    """
    if count is None:
      count = sizeof_words(buf)

    bufp = ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint16))

    BTI1553_MsgDataRd(bufp, count, msgaddr, self._hcore)


  def MsgDataWr (self, buf, msgaddr, count=None):
    """Writes the data associated with a message.  This function copies
    count data words from buf to the message structure specified by
    msgaddr.  If count is not given, it is calculated based on the
    size of buf.
    """
    if count is None:
      count = sizeof_words(buf)

    bufp = ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint16))

    BTI1553_MsgDataWr(bufp, count, msgaddr, self._hcore)


  def MsgFieldRd (self, field, msgaddr):
    """Reads the value of the field specified by field from the
    message structure at msgaddr. It is typically used to read the
    status words and error fields in a BC message structure after
    message transmission.

    Returns the value of the specified field in the specified message
    structure.
    """
    return BTI1553_MsgFieldRd(field, msgaddr, self._hcore)


  def MsgFieldWr (self, value, field, msgaddr):
    """Writes fieldvalue to the specified field of the specified
    message structure. This function can be used to reconfigure an
    existing message.

    Although all fields are writable, this function is typically only
    used to clear the hit bit in the FIELD1553_ERROR field. The hit
    bit indicates that the message has been transmitted or
    received.

    Returns None.
    """
    return BTI1553_MsgFieldWr(value, field, msgaddr, self._hcore)


  def RTConfig (self, taddr, flags=RTCFG1553_DEFAULT):
    """Configures a Remote Terminal (RT) for the specified channel with
    the options defined by flags.
    """
    errval = BTI1553_RTConfig(flags, taddr, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)


  def RTGetMsg (self, mcflag, taddr, rtxmit, saddr):
    """Obtains the message address for an existing message structure."""
    errval = \
      BTI1553_RTGetMsg(mcflag, taddr, rtxmit, saddr, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)

  def MonConfig(self, flags=MONCFG1553_DEFAULT):
    """Configures the device as a bus monitor"""
    errval = BTI1553_MonConfig(flags, self._channel, self._hcore)
    return BTIError.raise_if(errval, self.card)

  def SeqConfig(self, flags=SEQCFG_DEFAULT):
    """Configures the device sequential record"""
    errval = BTICard_SeqConfig(flags, self._hcore)
    return BTIError.raise_if(errval, self.card)


class BTICard (object):
  MAX_CARDS    = 4
  MAX_CORES    = 4
  MAX_CHANNELS = 32


  def __init__ (self, card=-1):
    """Creates a new BTICard for the given card number.  If not given,
    card numbers are scanned until the first suitable one found is
    successfully opened.
    """
    checkLibLoaded()
    super(BTICard, self).__init__()
    self._card  = None
    self._hcard = HCARD(0)
    self.open(card)


  def __open__ (self, card=-1):
    """Opens the given BTI 1553 card number."""
    if card >= 0:
      errval = BTICard_CardOpen(ctypes.byref(self._hcard), card)
      if errval is 0:
        self._card = card
    else:
      for card in range(0, BTICard.MAX_CARDS):
        errval = self.__open__(card)
        if errval is 0:
          break

    return errval


  def __repr__ (self):
    return "BTICard(card=%s)" % str(self.card)


  @property
  def _as_parameter_ (self):
    """The underlying BTI card handle."""
    return self._hcard


  @property
  def card (self):
    """The BTI card number.  Set via open()."""
    return self._card


  def close (self):
    """Closes this BTICard."""
    errval = BTICard_CardClose(self._hcard)
    if errval is 0:
      self._card        = None
      self._hcard.value = 0
    return BTIError.raise_if(errval, self.card)


  def open (self, card=-1):
    """Opens the given BTI 1553 card number.  If not given, card numbers
    are scanned and the first suitable one found is used.
    """
    if self._card is not None:
      self.close()

    errval = self.__open__(card)
    return BTIError.raise_if(errval, self.card)



class BTIEvent (object):
  FlagNames = filter(lambda s: s.startswith("EVENTTYPE_"), globals().keys())


  def __init__ (self, typeval=0, infoval=0, channel=0, hcore=0):
    self._typeval = ctypes.c_uint16(typeval)
    self._infoval = ctypes.c_uint32(infoval)
    self._channel = ctypes.c_int(channel)
    self._empty   = typeval is 0 and infoval is 0 and channel is 0
    self._hcore   = hcore


  def __repr__ (self):
    format = "BTIEvent(typeval=0x%02x, infoval=0x%04x, channel=%d, hcore=%d)"
    return format % (self.typeval, self.infoval, self.channel, self.hcore)


  def __str__ (self):
    env   = globals()
    names = filter(lambda s: self.typeval == env[s], BTIEvent.FlagNames)
    tname = (len(names) and names[0]) or str(self.typeval)
    empty = str(self.empty)
    return "%s <empty=%s, type=%s>" % (self.__repr__(), empty, tname)


  @property
  def c_values (self):
    """The underlying ctypes for typeval, infoval, and channel."""
    return (self._typeval, self._infoval, self._channel)


  @property
  def channel (self):
    """The event channel."""
    return self._channel.value


  @channel.setter
  def channel (self, value):
    self._channel.value = value
    self.empty          = False


  @property
  def empty (self):
    """Indicates whether or not this event is empty."""
    return self._empty


  @empty.setter
  def empty (self, value):
    self._empty = value
    if self._empty:
      self._typeval.value = 0
      self._infoval.value = 0
      self._channel.value = 0


  @property
  def hcore (self):
    """The core handle for this event."""
    return self._hcore.value


  @hcore.setter
  def hcore (self, value):
    self._hcore = value


  @property
  def infoval (self):
    """The event information field."""
    return self._infoval.value


  @infoval.setter
  def infoval (self, value):
    self._infoval.value = value
    self.empty          = False


  @property
  def typeval (self):
    """The event type.  Use isXXX properties to query specific types."""
    return self._typeval.value


  @typeval.setter
  def typeval (self, value):
    self._typeval.value = value
    self.empty          = False


  @property
  def is1553MSG (self):
    """MIL-STD-1553 message."""
    return self.typeval == EVENTTYPE_1553MSG


  @property
  def is1553OPCODE (self):
    """MIL-STD-1553 event log opcode."""
    return self.typeval == EVENTTYPE_1553OPCODE


  @property
  def is1553HALT (self):
    """MIL-STD-1553 schedule halt."""
    return self.typeval == EVENTTYPE_1553HALT


  @property
  def is1553PAUSE (self):
    """MIL-STD-1553 schedule pause."""
    return self.typeval == EVENTTYPE_1553PAUSE


  @property
  def is1553LIST (self):
    """MIL-STD-1553 list buffer empty/full."""
    return self.typeval == EVENTTYPE_1553


  @property
  def is1553SERIAL (self):
    """MIL-STD-1553 serial empty."""
    return self.typeval == EVENTTYPE_1553SERIAL


  @property
  def is429MSG (self):
    """ARINC 429 message."""
    return self.typeval == EVENTTYPE_429MSG


  @property
  def is429OPCODE (self):
    """ARINC 429 event log opcode."""
    return self.typeval == EVENTTYPE_429OPCODE


  @property
  def is429HALT (self):
    """ARINC 429 schedule halt."""
    return self.typeval == EVENTTYPE_429HALT


  @property
  def is429PAUSE (self):
    """ARINC 429 schedule pause."""
    return self.typeval == EVENTTYPE_429PAUSE


  @property
  def is429LIST (self):
    """ARINC 429 list buffer empty/full."""
    return self.typeval == EVENTTYPE_429


  @property
  def is429ERR (self):
    """ARINC 429 decoder error detected."""
    return self.typeval == EVENTTYPE_429ERR


  @property
  def is717WORD (self):
    """ARINC 717 word received."""
    return self.typeval == EVENTTYPE_717WORD


  @property
  def is717SUBFRM (self):
    """ARINC 717 sub frame completed."""
    return self.typeval == EVENTTYPE_717SUBFRM


  @property
  def is717SYNCERR (self):
    """ARINC 717 receive channel lost synchronization."""
    return self.typeval == EVENTTYPE_717SYNCERR


  @property
  def is708MSG (self):
    """ARINC 708 message."""
    return self.typeval == EVENTTYPE_708MSG


  @property
  def isSEQFULL (self):
    """Sequential record full."""
    return self.typeval == EVENTTYPE_SEQFULL


  @property
  def isSEQFREQ (self):
    """Sequential record frequency."""
    return self.typeval == EVENTTYPE_SEQFREQ


  @property
  def is422TXTHRESHOLD (self):
    """RS-422 TX under threshold."""
    return self.typeval == EVENTTYPE_422TXTHRESHOLD


  @property
  def is422TXFIFO (self):
    """RS-422 TX underflow."""
    return self.typeval == EVENTTYPE_422TXFIFO


  @property
  def is422RXTHRESHOLD (self):
    """RS-422 RX over threshold."""
    return self.typeval == EVENTTYPE_422RXTHRESHOLD


  @property
  def is422RXFIFO (self):
    """RS-422 RX overflow."""
    return self.typeval == EVENTTYPE_422RXFIFO


  @property
  def is422RXERROR (self):
    """RS-422 RX error."""
    return self.typeval == EVENTTYPE_422RXERROR


  @property
  def isCSDBMSG (self):
    """CSDB message."""
    return self.typeval == EVENTTYPE_CSDBMSG


  @property
  def isCSDBOPCODE (self):
    """CSDB event log opcode."""
    return self.typeval == EVENTTYPE_CSDBOPCODE


  @property
  def isCSDBHALT (self):
    """CSDB schedule halt."""
    return self.typeval == EVENTTYPE_CSDBHALT


  @property
  def isCSDBPAUSE (self):
    """CSDB schedule pause."""
    return self.typeval == EVENTTYPE_CSDBPAUSE


  @property
  def isCSDBLIST (self):
    """CSDB list buffer empty/full."""
    return self.typeval == EVENTTYPE_CSDB


  @property
  def isCSDBERR (self):
    """CSDB decoder error detected."""
    return self.typeval == EVENTTYPE_CSDBERR


  @property
  def isCSDBSYNCERR (self):
    """CSDB receive channel lost synchronization."""
    return self.typeval == EVENTTYPE_CSDBSYNCERR


  @property
  def isDIOEDGE (self):
    """DIO edge event."""
    return self.typeval == EVENTTYPE_DIOEDGE


  @property
  def isDIOFAULT (self):
    """DIO fault event."""
    return self.typeval == EVENTTYPE_DIOFAULT


  @property
  def isBITERROR (self):
    """Built-in Test error event."""
    return self.typeval == EVENTTYPE_BITERROR



class BTIError (Exception):
  def __init__ (self, errval=-1, card=None):
    """Creates a new BTIError based on the given error value and BTI
    card.  If no error value is given, it defaults to -1: "ERR_UNKNOWN
    An unexpected error occurred (BTICard)."
    """
    cardnum = 0
    if isinstance(card, BTICard):
      cardnum = card.card
    elif type(card) is int:
      cardnum = card

    msg = BTICard_ErrDescStr(errval, cardnum)
    super(BTIError, self).__init__(msg)

    self._errval = errval
    self._card   = card


  @property
  def card (self):
    """The BTICard which generated this error."""
    return self._card


  @property
  def errval (self):
    """The error value."""
    return self._errval


  @staticmethod
  def raise_if (errval, card=None):
    """Raises a BTIError if errval is negative, otherwise return errval.

    This behavior would be more elegantly expressed as a Python
    decorator.  Unfortunately, decorators do not preserve method
    signatures (e.g. when using Pydoc's help()), even when using
    functools.wraps().
    """
    if type(errval) is int and errval < 0:
      raise BTIError(errval, card)
    else:
      return errval



class MsgErr1553 (object):
  FlagNames = filter(lambda s: s.startswith("MSGERR1553_"), globals().keys())


  def __init__ (self, errflags):
    """Creates a new MsgErr1553 object with the given error flags."""
    self._errflags = errflags


  def __repr__ (self):
    return "MsgErr1553(errflags=0x%04x)" % self.errflags


  def __str__ (self):
    env   = globals()
    names = filter(lambda s: self.errflags & env[s], MsgErr1553.FlagNames)
    return "%s (%s)" % (self.__repr__(), ", ".join(names))


  @property
  def errflags (self):
    """The message error flags."""
    return self._errflags


  @property
  def isNORESP (self):
    """No response was received from the RT."""
    return self._errflags & MSGERR1553_NORESP is not 0


  @property
  def isANYERR (self):
    """Set if any other error bits are set."""
    return self._errflags & MSGERR1553_ANYERR is not 0


  @property
  def isPROTOCOL (self):
    """A protocol error occurred."""
    return self._errflags & MSGERR1553_PROTOCOL is not 0


  @property
  def isSYNC (self):
    """Wrong polarity of the sync pulse."""
    return self._errflags & MSGERR1553_SYNC is not 0


  @property
  def isDATACOUNT (self):
    """Too many/too few data words."""
    return self._errflags & MSGERR1553_DATACOUNT is not 0


  @property
  def isMANCH (self):
    """Manchester error."""
    return self._errflags & MSGERR1553_MANCH is not 0


  @property
  def isPARITY (self):
    """Parity error."""
    return self._errflags & MSGERR1553_PARITY is not 0


  @property
  def isWORD (self):
    """Word error."""
    return self._errflags & MSGERR1553_WORD is not 0


  @property
  def isRETRY (self):
    """All attempts to retry transmission of this message failed
    (BC only).
    """
    return self._errflags & MSGERR1553_RETRY is not 0


  @property
  def isSYSTEM (self):
    """Internal system error occurred."""
    return self._errflags & MSGERR1553_SYSTEM is not 0


  @property
  def isHIT (self):
    """Indicates that this message was transmitted or received since
    this bit was last cleared (always set).
    """
    return self._errflags & MSGERR1553_HIT



class XmitFields1553 (ctypes.Structure):
  _fields_ = [
    ( "ctrlflags" , ctypes.c_uint32 ),
    ( "flag1"     , ctypes.c_uint16 ),
    ( "flag2"     , ctypes.c_uint16 ),
    ( "errflags"  , ctypes.c_uint16 ),
    ( "actflags"  , ctypes.c_uint16 ),
    ( "resptime1" , ctypes.c_uint16 ),
    ( "resptime2" , ctypes.c_uint16 ),
    ( "datacount" , ctypes.c_uint16 ),
    ( "extflag"   , ctypes.c_uint16 ),
    ( "timetag"   , ctypes.c_uint32 ),
    ( "elapsetime", ctypes.c_uint32 ),
    ( "preaddr"   , ctypes.c_uint32 ),
    ( "postaddr"  , ctypes.c_uint32 ),
    ( "timetagh"  , ctypes.c_uint32 ),
    ( "resv18"    , ctypes.c_uint16 ),
    ( "resv19"    , ctypes.c_uint16 ),
    ( "cwd1"      , ctypes.c_uint16 ),
    ( "cwd2"      , ctypes.c_uint16 ),
    ( "swd1"      , ctypes.c_uint16 ),
    ( "swd2"      , ctypes.c_uint16 ),
    ( "_data"     , ctypes.c_uint16 * 32 ),
    ( "extra"     , ctypes.c_uint16 *  8 ),
  ]


  def __init__ (self, taddr, rtxmit, saddr, *args, **kwargs):
    """XmitFields1553(taddr, rtxmit, saddr[, mcode[, data]])

    Creates a new BTI 1553 Message with the given terminal address,
    T/R bit, subaddress and optional mode code or message data.
    """
    checkLibLoaded()
    super(XmitFields1553, self).__init__()
    self.ctrlflags = MSGCRT1553_DEFAULT
    data           = None
    self.__pack__(taddr, rtxmit, saddr, 0)

    if 'data' in kwargs:
      data = kwargs['data']
    elif len(args) is 1 and type(args[0]) is list or type(args[0]) is str:
      data = args[0]

    if data:
      self.data  = data
    elif 'mcode' in kwargs:
      self.mcode = kwargs['mcode']
    elif len(args) is 1 and type(args[0]) is int:
      self.mcode = args[0]


  def __pack__ (self, taddr=None, rtxmit=None, saddr=None, wcmc=None):
    """Packs the terminal address, T/R bit, subaddress, and mode code."""
    _taddr, _rtxmit, _saddr, _wcmc = self.__unpack__()
    if taddr  is None: taddr  = _taddr
    if rtxmit is None: rtxmit = _rtxmit
    if saddr  is None: saddr  = _saddr
    if wcmc   is None: wcmc   = _wcmc
    self.cwd1 = BTI1553_ValPackCWD(taddr, rtxmit, saddr, wcmc)


  def __str__ (self):
    format = "%s(taddr=%d, rtxmit=%d, saddr=%d) <wcmc=%d>"
    name   = self.__class__.__name__
    values = self.__unpack__()
    return format % (name, values[0], values[1], values[2], values[3])


  def __unpack__ (self):
    taddr  = ctypes.c_int()
    rtxmit = ctypes.c_int()
    saddr  = ctypes.c_int()
    wcmc   = ctypes.c_int()
    BTI1553_ValUnpackCWD( self.cwd1,
                          ctypes.byref( taddr  ),
                          ctypes.byref( rtxmit ),
                          ctypes.byref( saddr  ),
                          ctypes.byref( wcmc   ) )
    return taddr.value, rtxmit.value, saddr.value, wcmc.value


  @property
  def data (self):
    """The message data."""
    return self._data


  @data.setter
  def data (self, values):
    if values is None:
      ctypes.memset(self._data, 0, ctypes.sizeof(self._data))
      self.wcount = 0
    elif isinstance(values, list) or isinstance(values, tuple):
      self._data  = values
      self.wcount = len(values)
    elif type(values) == bytearray or type(values) == str:
      values = bytearray(values)
      wcount = len(values) / 2
      d      = 0
      for n in range(1, len(values), 2):
        self._data[d] = (values[n - 1] << 8) | values[n]
        d += 1
      if len(values) % 2 == 1:
        self._data[d]  = (values[-1] << 8)
        wcount        += 1
      self.wcount = wcount


  @property
  def errors (self):
    """The message error flags."""
    return MsgErr1553(self.errflags)


  @property
  def mcode (self):
    """The mode code."""
    return self.__unpack__()[3]


  @mcode.setter
  def mcode (self, value):
    self.__pack__(wcmc=value)


  @property
  def rtxmit (self):
    """Indicates whether the Remote Terminal (RT) is expected to transmit."""
    return self.__unpack__()[1]


  @rtxmit.setter
  def rtxmit (self, value):
    self.__pack__(rtxmit=value)


  @property
  def saddr (self):
    """The terminal subaddress."""
    return self.__unpack__()[2]


  @saddr.setter
  def saddr (self, value):
    self.__pack__(saddr=value)


  @property
  def taddr (self):
    """The terminal address."""
    return self.__unpack__()[0]


  @taddr.setter
  def taddr (self, value):
    self.__pack__(taddr=value)


  @property
  def wcount (self):
    """The word count."""
    return self.__unpack__()[3]


  @wcount.setter
  def wcount (self, value):
    self.__pack__(wcmc=value)


class cwd:
  def __init__(self, cwd_word):
    self._cwd = cwd_word

  @property
  def taddr(self):
    return (self._cwd & 0xf800) >> 11

  @property
  def rtxmit(self):
    return ((self._cwd & 0x400) >> 10)

  @property
  def saddr(self):
    return ((self._cwd & 0x3e0) >> 5)

  @property
  def wcmc(self):
    return (self._cwd & 0x1f)

  def __str__(self):
    format = "%s(taddr=%d, rtxmit=%d, saddr=%d) <wcmc=%d>"
    name = self.__class__.__name__
    return format % (name, self.taddr, self.rtxmit, self.saddr, self.wcmc)

class swd:
  def __init__(self, swd_word):
    self._swd = swd_word

  @property
  def taddr(self):
    return (self._swd & 0xf800) >> 11

  @property
  def code(self):
    return (self._swd & 0x7ff)

  def __str__(self):
    format = "%s(taddr=%d, code=%x)"
    name = self.__class__.__name__
    return format % (name, self.taddr, self.code)

class SEQFINDINFO(ctypes.Structure):
  _fields_ = [
    ("pRecFirst", ctypes.POINTER(ctypes.c_uint16)),
    ("pRecNext" , ctypes.POINTER(ctypes.c_uint16)),
    ("pRecLast" , ctypes.POINTER(ctypes.c_uint16))
  ]


class SEQRECORD1553(ctypes.Structure):
  _fields_ = [
    ("type"      , ctypes.c_uint16),
    ("count"     , ctypes.c_uint16),
    ("timestamp" , ctypes.c_uint32),
    ("activity"  , ctypes.c_uint16),
    ("error"     , ctypes.c_uint16),
    ("_cwd1"      , ctypes.c_uint16),
    ("_cwd2"      , ctypes.c_uint16),
    ("_swd1"      , ctypes.c_uint16),
    ("_swd2"      , ctypes.c_uint16),
    ("datacount" , ctypes.c_uint16),
    ("_data"     , ctypes.c_uint16 * 40)
  ]

  @property
  def cwd1(self):
    return cwd(self._cwd1)

  @property
  def cwd2(self):
    return cwd(self._cwd2)

  @property
  def swd1(self):
    return swd(self._swd1)

  @property
  def swd2(self):
    return swd(self._swd2)

  def __str__(self):
    format = "%s(type=%d, count=%d, timestamp=%d, activity=%d, error=%d"
    name = self.__class__.__name__
    return (format % (name, self.type, self.count, self.timestamp, self.activity,
      self.error) + " cwd1:" + str(self.cwd1) + " cwd2:" + str(self.cwd2)
      + " swd1:" + str(self.swd1) + " swd2:" + str(self.swd2))

  def tostring(self):
    return buffer(self)[:]

  @classmethod
  def frombytes(cls, rawbytes):
    sr = cls()
    ctypes.memmove(ctypes.addressof(sr), rawbytes, ctypes.sizeof(sr))
    return sr

  @property
  def data(self):
    short_sz = ctypes.sizeof(ctypes.c_uint16)
    return buffer(self, ctypes.sizeof(self) - short_sz*40 - short_sz, 40)

  def __unpack__(self):
    return self.cwd1.taddr, self.cwd1.rtxmit, self.cwd1.saddr, self.cwd1.wcmc


class SEQRECORDMORE1553(ctypes.Structure):
  _fields_ = [
    ("timestamph", ctypes.c_uint32),
    ("resptime1", ctypes.c_uint16),
    ("resptime2", ctypes.c_uint16)
  ]

  def tostring(self):
    return buffer(self)[:]

  def __str__(self):
    format = "%s(timestamph=%d, resptime1=%d, resptime2=%d)"
    name = self.__class__.__name__
    return format % (name, self.timestamph, self.resptime1, self.resptime2)
