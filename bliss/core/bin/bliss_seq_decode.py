#!/usr/bin/env python
'''

usage: bliss-seq-decode oco3_seq_SSS_NNN_desc.bin

Decodes the given relative time command sequence to text.

Examples:

  $ bliss-seq-decode seq/oco3_seq_gps_001_reset.bin
'''

import os
import sys
import argparse

from bliss.core import gds, log, seq


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Add required command line arguments
    parser.add_argument('filename',default=None)

    # Get command line arguments
    args = vars(parser.parse_args())

    filename  = os.path.abspath(args['filename'])
    extension = os.path.splitext(filename)[1]

    if extension.lower() != '.bin':
        log.warn("Filename '%s' does not have a '.bin' extension", filename)

    sequence = seq.Seq(filename)

    if not sequence.validate():
        for msg in sequence.messages:
            log.error(msg)
    else:
        txtpath = sequence.txtpath
        seqid   = sequence.seqid
        version = sequence.version

        msg = "Writing %s (seqid=0x%04x, version=%u)."
        log.info(msg, txtpath, seqid, version)

        sequence.writeText()

    log.end()


if __name__ == '__main__':
    main()
