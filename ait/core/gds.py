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

"""
AIT Ground Data System

The ait.core.gds module provides utility functions specific to GDS
command-line tools.
"""

from typing import Optional, ByteString
import zlib

from ait.core import log


def compress(input_filename, output_filename=None, verbose=False):
    """compress(input_filename, output_filename=None, verbose=False) -> integer

    Uses zlib to compress input_filename and store the result in
    output_filename.  The size of output_filename is returned on
    success; zero is returned on failure.

    The input file is compressed in one fell swoop.  The output_filename
    defaults to input_filename + ".ait-zlib".

    If verbose is True, compress() will use ait.core.log.info() to
    report compression statistics.
    """
    input_size = 0
    output_size = 0

    if output_filename is None:
        output_filename = input_filename + ".ait-zlib"

    try:
        stream = open(input_filename, "rb")
        output = open(output_filename, "wb")
        bytes = stream.read()
        input_size = len(bytes)

        if verbose:
            log.info("Compressing %s (%d bytes).", input_filename, input_size)

        compressed = zlib.compress(bytes, 3)
        output_size = len(compressed)
        output.write(compressed)

        stream.close()
        output.close()

        percent = (1.0 - (output_size / float(input_size))) * 100

        if verbose:
            log.info("Wrote %s (%d bytes).", output_filename, output_size)
            log.info("Compressed %6.2f percent", percent)

    except OSError as e:
        log.error(str(e) + ".")

    return output_size


def hexdump(bytes, addr=None, preamble=None, printfunc=None, stepsize=16):
    """hexdump(bytes[, addr[, preamble[, printfunc[, stepsize=16]]]])

    Outputs bytes in hexdump format lines similar to the following (here
    preamble='Bank1', stepsize=8, and len(bytes) == 15)::

      Bank1: 0xFD020000: 7f45  4c46  0102  0100  *.ELF....*
      Bank1: 0xFD020008: 0000  0000  0000  00    *....... *

    Where stepsize controls the number of bytes per line.  If addr is
    omitted, the address portion of the hexdump will not be output.
    Lines will be passed to printfunc for output, or Python's builtin
    print, if printfunc is omitted.

    If a byte is not in the range [32, 127), a period will rendered for
    the character portion of the output.
    """
    if preamble is None:
        preamble = ""

    bytes = bytearray(bytes)
    size = len(bytes)

    for n in range(0, size, stepsize):
        if addr is not None:
            dump = preamble + "0x%04X: " % (addr + n)
        else:
            dump = preamble
        end = min(size, n + stepsize)
        dump += hexdump_line(bytes[n:end], stepsize)

        if printfunc is None:
            print(dump)
        else:
            printfunc(dump)


def hexdump_line(_bytes: ByteString, length: Optional[int] = None) -> str:
    """Create a hexdump formatted line for supplied bytes.

    If length is greater than len(_bytes), the line will be padded with ASCII
    space characters to indicate no byte data is present.

    Arguments:
        _bytes: The bytes to format.

        length (optional): The optional length of the output line. This should be
            greater than the length of bytes if provided.

    Returns:
        The hexdump formatted line.
    """
    line = ""

    if length is None:
        length = len(_bytes)

    for n in range(0, length, 2):
        if n < len(_bytes) - 1:
            line += "%02x%02x  " % (_bytes[n], _bytes[n + 1])
        elif n < len(_bytes):
            line += "%02x    " % _bytes[n]
        else:
            line += "      "

    line += "*"

    for n in range(length):
        if n < len(_bytes):
            if _bytes[n] in range(32, 127):
                line += "%c" % _bytes[n]
            else:
                line += "."
        else:
            line += " "

    line += "*"
    return line
