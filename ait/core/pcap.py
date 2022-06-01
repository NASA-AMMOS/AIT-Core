# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
This module, pcap.py, is a library to read/write PCAP-formatted files with
simple open, read, write, close functions.  (PCAP - packet capture)
"""

import builtins
import calendar
import math
import struct
import datetime

from .dmc import get_timestamp_utc
from ait.core import log

"""
Check the endian of the host we are currently running on.
"""
if struct.pack("@I", 0xA1B2C3D4) == struct.pack(">I", 0xA1B2C3D4):
    EndianSwap = "<"
else:
    EndianSwap = ">"


class PCapFileStats(object):
    """Current and threshold and statistics in PCapRolloverStream"""

    __slots__ = "nbytes", "npackets", "nseconds"

    def __init__(self, nbytes=None, npackets=None, nseconds=None):
        self.nbytes = nbytes
        self.npackets = npackets
        self.nseconds = nseconds


class PCapGlobalHeader:
    """PCapGlobalHeader

    Represents a PCap global header.  See:

        https://wiki.wireshark.org/Development/LibpcapFileFormat
    """
    def __init__(self, stream=None):
        """Creates a new PCapGlobalHeader with default values.  If a stream
        is given, the global header data is read from it.
        """
        self._format = "IHHiIII"
        self._size = struct.calcsize(self._format)
        self._swap = "@"

        if stream is None:
            self.magic_number = 0xA1B2C3D4  # detects file format and byte ordering
            self.version_major = 2
            self.version_minor = 4
            self.thiszone = 0       # GMT to local correction (0 == GMT)
            self.sigfigs = 0        # accuracy of timestamps
            self.snaplen = 65535    # max length of captured packets, in octets
            self.network = 147      # data link type  (147-162 are reserved for private use)
            self._data = self.pack()
        else:
            self.read(stream)

    def __len__(self):
        """Returns the number of bytes in this PCapGlobalHeader."""
        return len(self._data)

    def __str__(self):
        """Returns this PCapGlobalHeader as a binary string."""
        return f'PCapGlobalHeader Class: \r\n   format={self._format}, magic number={self.magic_number},'\
               f'major version={self.version_major}, minor version={self.version_minor}, \r\n' \
               f'   time zone={self.thiszone}, timestamp accuracy={self.sigfigs}, max packet size={self.snaplen}, '\
               f'network={self.network}'

    def pack(self):
        return struct.pack(
            self._format,
            self.magic_number,
            self.version_major,
            self.version_minor,
            self.thiszone,
            self.sigfigs,
            self.snaplen,
            self.network,
        )

    def incomplete(self):
        """Indicates whether or not this PCapGlobalHeader is incomplete."""
        return len(self) < self._size

    def read(self, stream):
        """Reads PCapGlobalHeader data from the given stream."""
        self._data = stream.read(self._size)

        if len(self._data) >= self._size:
            values = struct.unpack(self._format, self._data)
        else:
            values = None, None, None, None, None, None, None

        if values[0] == 0xA1B2C3D4 or values[0] == 0xA1B23C4D:
            self._swap = "@"
        elif values[0] == 0xD4C3B2A1 or values[0] == 0x4D3CB2A1:
            self._swap = EndianSwap

        if values[0] is not None:
            values = struct.unpack(self._swap + self._format, self._data)

        self.magic_number = values[0]
        self.version_major = values[1]
        self.version_minor = values[2]
        self.thiszone = values[3]
        self.sigfigs = values[4]
        self.snaplen = values[5]
        self.network = values[6]


class PCapPacketHeader:
    """PCapPacketHeader

    Represents a PCap packet header.  See:

        https://wiki.wireshark.org/Development/LibpcapFileFormat
    """

    def __init__(self, stream=None, swap=None, orig_len=0, maxlen=65535):
        """Creates a new PCapPacketHeader with default values.  If a stream is
        given, the packet header data is read from it.
        """

        if swap is None:
            swap = "@"

        self._format = "IIII"
        self._size = struct.calcsize(self._format)
        self._swap = swap

        if stream is None:
            self.ts_sec, self.ts_usec = get_timestamp_utc()
            self.incl_len = min(orig_len, maxlen)
            self.orig_len = orig_len
            self._data = self.pack()
        else:
            self.read(stream)

    def __len__(self):
        """Returns the number of bytes in this PCapPacketHeader."""
        return len(self._data)

    def __str__(self):
        """Returns this PCapPacketHeader as a binary string."""

        return f'PCapPacketHeader Class: \r\n   format={self._format}, timestamp seconds={self.ts_sec},' \
               f'timestamp microseconds={self.ts_usec}.\r\n   number of octets in file={self.incl_len}, ' \
               f'actual length of packet={self.orig_len}'

    def pack(self):
        """Returns this PCapPacketHeader as a binary string."""
        return struct.pack(
            self._format, self.ts_sec, self.ts_usec, self.incl_len, self.orig_len
        )

    @property
    def timestamp(self):
        """Packet timestamp as a Python Datetime object"""
        return datetime.datetime.utcfromtimestamp(self.ts)

    @property
    def ts(self):
        """Packet timestamp as a float, a combination of ts_sec and ts_usec"""
        return float(self.ts_sec) + (float(self.ts_usec) / 1e6)

    def incomplete(self):
        """Indicates whether or not this PCapGlobalHeader is incomplete."""
        return len(self) < self._size

    def read(self, stream):
        """Reads PCapPacketHeader data from the given stream."""
        self._data = stream.read(self._size)

        if len(self._data) >= self._size:
            values = struct.unpack(self._swap + self._format, self._data)
        else:
            values = None, None, None, None

        self.ts_sec = values[0]
        self.ts_usec = values[1]
        self.incl_len = values[2]
        self.orig_len = values[3]


class PCapRolloverStream:
    """
    Wraps a PCapStream to rollover to a new filename, based on packet
    times, file size, or number of packets.
    """

    def __init__(self, format, nbytes=None, npackets=None, nseconds=None, dryrun=False):
        """Creates a new :class:`PCapRolloverStream` with the given
        thresholds.

        A :class:`PCapRolloverStream` behaves like a
        :class:`PCapStream`, except that writing a new packet will
        cause the current file to be closed and a new file to be
        opened when one or more of thresholds (``nbytes``,
        ``npackets``, ``nseconds``) is exceeded.

        The new filename is determined by passing the ``format``
        string through :func:`PCapPacketHeader.timestamp.strftime()`
        for the first packet in the file.

        When segmenting based on time (``nseconds``), for file naming
        and interval calculation purposes ONLY, the timestamp of the
        first packet in the file is rounded down to nearest even
        multiple of the number of seconds.  This yields nice round
        number timestamps for filenames.  For example:

          PCapRolloverStream(format="%Y%m%dT%H%M%S.pcap", nseconds=3600)

        If the first packet written to a file has a time of 2017-11-23
        19:28:58, the file will be named:

            20171123T190000.pcap

        And a new file will be started when a packet is written with a
        timestamp that exceeds 2017-11-23 19:59:59.

        :param format:    Output filename in ``strftime(3)`` format
        :param nbytes:    Rollover after writing nbytes
        :param npackets:  Rollover after writing npackets
        :param nseconds:  Rollover after nseconds have elapsed between
                          the first and last packet timestamp in the file.
        :param dryrun:    Simulate file writes and output log messages.
        """
        self._dryrun = dryrun
        self._filename = None
        self._format = format
        self._startTime = None
        self._stream = None
        self._threshold = PCapFileStats(nbytes, npackets, nseconds)
        self._total = PCapFileStats(0, 0, 0)

    @property
    def rollover(self):
        """Indicates whether or not its time to rollover to a new file."""
        rollover = False

        if not rollover and self._threshold.nbytes is not None:
            rollover = self._total.nbytes >= self._threshold.nbytes

        if not rollover and self._threshold.npackets is not None:
            rollover = self._total.npackets >= self._threshold.npackets

        if not rollover and self._threshold.nseconds is not None:
            nseconds = math.ceil(self._total.nseconds)
            rollover = nseconds >= self._threshold.nseconds

        return rollover

    def write(self, bytes, header=None):
        """Writes packet ``bytes`` and the optional pcap packet ``header``.

        If the pcap packet ``header`` is not specified, one will be
        generated based on the number of packet ``bytes`` and current
        time.
        """
        if header is None:
            header = PCapPacketHeader(orig_len=len(bytes))

        if self._stream is None:
            if self._threshold.nseconds is not None:
                # Round down to the nearest multiple of nseconds
                nseconds = self._threshold.nseconds
                remainder = int(math.floor(header.ts % nseconds))
                delta = datetime.timedelta(seconds=remainder)
                timestamp = header.timestamp - delta
            else:
                timestamp = header.timestamp

            self._filename = timestamp.strftime(self._format)
            self._startTime = calendar.timegm(
                timestamp.replace(microsecond=0).timetuple()
            )

            if self._dryrun:
                self._stream = True
                self._total.nbytes += len(PCapGlobalHeader().pack())
            else:
                self._stream = open(self._filename, "w")
                self._total.nbytes += len(self._stream.header.pack())

        if not self._dryrun:
            self._stream.write(bytes, header)

        self._total.nbytes += len(bytes) + len(header)
        self._total.npackets += 1
        self._total.nseconds = header.ts - self._startTime

        if self.rollover:
            self.close()

        return header.incl_len

    def close(self):
        """Closes this :class:``PCapStream`` by closing the underlying Python
        stream."""
        if self._stream:
            values = (
                self._total.nbytes,
                self._total.npackets,
                int(math.ceil(self._total.nseconds)),
                self._filename,
            )

            if self._dryrun:
                msg = "Would write {} bytes, {} packets, {} seconds to {}."
            else:
                msg = "Wrote {} bytes, {} packets, {} seconds to {}."
                self._stream.close()

            log.info(msg.format(*values))

            self._filename = None
            self._startTime = None
            self._stream = None
            self._total = PCapFileStats(0, 0, 0)


class PCapStream:
    """PCapStream

    PCapStream is the primary class of the pcap.py module.  It exposes
    open(), read(), write(), and close() methods to read and write
    pcap-formatted files.

    See:

        https://wiki.wireshark.org/Development/LibpcapFileFormat
    """

    def __init__(self, stream, mode="rb"):
        """Creates a new PCapStream, which wraps the underlying Python stream,
        already opened in the given mode.
        """
        if mode.startswith("r"):
            self.header = PCapGlobalHeader(stream)
        elif mode.startswith("w") or (mode.startswith("a") and stream.tell() == 0):
            self.header = PCapGlobalHeader()
            stream.write(self.header.pack())

        self._stream = stream

    def __enter__(self):
        """A PCapStream provies a Python Context Manager interface."""
        return self

    def __exit__(self, type, value, traceback):
        """A PCapStream provies a Python Context Manager interface."""
        self.close()

    def __next__(self):
        """Provides Python 3 iterator compatibility.  See next()."""
        return self.next()

    def __iter__(self):
        """A PCapStream provides a Python iterator interface."""
        return self

    def next(self):
        """Returns the next header and packet from this
        PCapStream. See read().
        """
        header, packet = self.read()

        if packet is None:
            raise StopIteration

        return header, packet

    def read(self):
        """Reads a single packet from the this pcap stream, returning a
        tuple (PCapPacketHeader, packet)
        """
        header = PCapPacketHeader(self._stream, self.header._swap)
        packet = None

        if not header.incomplete():
            packet = self._stream.read(header.incl_len)

        return (header, packet)

    def write(self, bytes, header=None):
        """write() is meant to work like the normal file write().  It takes
        two arguments, a byte array to write to the file as a single
        PCAP packet, and an optional header if one already exists.
        The length of the byte array should be less than 65535 bytes.
        write() returns the number of bytes actually written to the file.
        """
        if type(bytes) is str:
            bytes = bytearray(bytes, "ISO-8859-1")

        if not isinstance(header, PCapPacketHeader):
            header = PCapPacketHeader(orig_len=len(bytes))

        packet = bytes[0 : header.incl_len]

        self._stream.write(header.pack())
        self._stream.write(packet)
        self._stream.flush()

        return header.incl_len

    def close(self):
        """Closes this PCapStream by closing the underlying Python stream."""
        self._stream.close()


def open(filename, mode="r", **options):
    """Returns an instance of a :class:`PCapStream` class which contains
    the ``read()``, ``write()``, and ``close()`` methods.  Binary mode
    is assumed for this module, so the "b" is not required when
    calling ``open()``.

    If the optiontal ``rollover`` parameter is True, a
    :class:`PCapRolloverStream` is created instead.  In that case
    ``filename`` is treated as a ``strftime(3)`` format string and
    ``nbytes``, ``npackets``, ``nseconds``, and ``dryrun`` parameters
    may also be specified.  See :class:``PCapRolloverStream`` for more
    information.

    NOTE: :class:`PCapRolloverStream` is always opened in write mode
    ("wb") and supports only ``write()`` and ``close()``, not
    ``read()``.
    """
    mode = mode.replace("b", "") + "b"

    if options.get("rollover", False):
        stream = PCapRolloverStream(
            filename,
            options.get("nbytes", None),
            options.get("npackets", None),
            options.get("nseconds", None),
            options.get("dryrun", False),
        )
    else:
        stream = PCapStream(builtins.open(filename, mode), mode)

    return stream


def query(starttime, endtime, output=None, *filenames):
    """Given a time range and input file, query creates a new file with only
    that subset of data. If no outfile name is given, the new file name is the
    old file name with the time range appended.

    Args:
        starttime:
            The datetime of the beginning time range to be extracted from the files.
        endtime:
            The datetime of the end of the time range to be extracted from the files.
        output:
            Optional: The output file name. Defaults to
            [first filename in filenames][starttime]-[endtime].pcap
        filenames:
            A tuple of one or more file names to extract data from.
    """

    if not output:
        output = (
            filenames[0].replace(".pcap", "")
            + starttime.isoformat()
            + "-"
            + endtime.isoformat()
            + ".pcap"
        )
    else:
        output = output

    with open(output, "w") as outfile:
        for filename in filenames:
            log.info("pcap.query: processing %s..." % filename)
            with open(filename, "r") as stream:
                for header, packet in stream:
                    if packet is not None:
                        if (
                                starttime <= header.timestamp <= endtime
                        ):
                            outfile.write(packet, header=header)


def segment(filenames, format, **options):
    """Segment the given pcap file(s) by one or more thresholds
    (``nbytes``, ``npackets``, ``nseconds``).  New segment filenames
    are determined based on the ``strftime(3)`` ``format`` string
    and the timestamp of the first packet in the file.

    :param filenames: Single filename (string) or list of filenames
    :param format:    Output filename in ``strftime(3)`` format
    :param nbytes:    Rollover after writing N bytes
    :param npackets:  Rollover after writing N packets
    :param nseconds:  Rollover after N seconds have elapsed between
                      the first and last packet timestamp in the file.
    :param dryrun:    Simulate file writes and output log messages.
    """
    output = open(format, rollover=True, **options)

    if isinstance(filenames, str):
        filenames = [filenames]

    for filename in filenames:
        with open(filename, "r") as stream:
            for header, packet in stream:
                output.write(packet, header)

    output.close()


def times(filenames, tolerance=2):
    """For the given file(s), return the time ranges available.  Tolerance
    sets the number of seconds between time ranges.  Any gaps larger
    than tolerance seconds will result in a new time range.

    :param filenames: Single filename (string) or list of filenames
    :param tolerance: Maximum seconds between contiguous time ranges

    :returns: A dictionary keyed by filename, with each value a list
    of (start, stop) time ranges for that file.
    """
    times = {}
    delta = datetime.timedelta(seconds=tolerance)

    if isinstance(filenames, str):
        filenames = [filenames]

    for filename in filenames:
        with open(filename, "r") as stream:
            times[filename] = list()
            header, packet = stream.read()
            start, stop = header.timestamp, header.timestamp

            for header, _packet in stream:
                if header.timestamp - stop > delta:
                    times[filename].append((start, stop))
                    start = header.timestamp
                stop = header.timestamp

            times[filename].append((start, stop))

    return times
