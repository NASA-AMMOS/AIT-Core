#!/usr/bin/env python
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

usage: ait-seq-decode ait_seq_SSS_desc_NNN.bin

Decodes the given relative time command sequence to text.

Examples:

  $ ait-seq-decode seq/ait_seq_gps_reset_001.bin
"""
import argparse
import os

from ait.core import log
from ait.core import seq


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add required command line arguments
    parser.add_argument(
        "filename", nargs="+", metavar="</path/to/seq>", help="encoded sequence file(s)"
    )

    # Get command line arguments
    args = parser.parse_args()
    for fname in args.filename:
        filename = os.path.abspath(fname)
        if not os.path.isfile(filename):
            raise Exception("File not found: %s " % filename)

        extension = os.path.splitext(filename)[1]

        if extension.lower() != ".bin":
            log.warn("Filename '%s' does not have a '.bin' extension", filename)

        # Parse the filename for the applicable information
        parts = os.path.basename(filename).split("_")
        seqid = os.path.splitext(parts[-1])[0]

        try:
            int(seqid)
        except ValueError:
            raise Exception(
                'Invalid filename "%s": . %s' % (os.path.basename(filename), __doc__)
            )

    sequence = seq.createSeq(filename, id=seqid)

    if not sequence.validate():
        for msg in sequence.messages:
            log.error(msg)
    else:
        txtpath = sequence.txtpath
        seqid = sequence.seqid
        version = sequence.version

        msg = "Writing %s (seqid=0x%04x, version=%u)."
        log.info(msg, txtpath, seqid, version)

        sequence.write_text()

    log.end()


if __name__ == "__main__":
    main()
