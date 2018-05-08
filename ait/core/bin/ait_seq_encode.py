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

'''
usage:  ait-seq-encode mission_seq_SSS_desc_NNN.txt
where:
        SSS  = subsystem
        desc = sequence descriptor
        NNN  = sequence ID (integer)

Encodes the given relative time command sequence to binary.

Examples:

  $ ait-seq-encode seq/oco3_seq_gps_reset_001.txt
'''

import os
import sys
import argparse

from ait.core import gds, log, seq


def main():
    log.begin()

    try:
        defaults      = { }
        parser = argparse.ArgumentParser(
            description = __doc__,
            formatter_class = argparse.RawDescriptionHelpFormatter)

        # Add required command line arguments
        parser.add_argument('filename',
            nargs='+',
            metavar='</path/to/seq>',
            help='File or collection of sequence file(s)')

        # Add optional command line arguments
        args = parser.parse_args()

        for fname in args.filename:
            filename  = os.path.abspath(fname)
            if not os.path.isfile(filename):
                raise Exception('File not found: %s ' % filename)

            extension = os.path.splitext(filename)[1]

            if extension.lower() != '.txt':
                log.warn("Filename '%s' does not have a '.txt' extension", filename)

            # Parse the filename for the applicable information
            parts = os.path.basename(filename).split('_')
            l = len(parts)
            seqid = os.path.splitext(parts[l-1])[0]
            desc = parts[l-2]
            subsys = parts[l-3]

            try:
                int(seqid)
            except ValueError:
                raise Exception('Invalid filename "%s": . %s' % (os.path.basename(filename), __doc__))

            sequence = seq.Seq(filename, id=seqid)

            if not sequence.validate():
                for msg in sequence.log.messages:
                    log.error(msg)
            else:
                binpath = sequence.binpath
                seqid   = sequence.seqid

                log.info("Writing %s (seqid=0x%04x).", binpath, seqid)
                sequence.writeBinary()

            exit = 0
    except Exception, e:
        log.error(e)
        exit = 1

    log.end()

    sys.exit(exit)


if __name__ == '__main__':
    main()
