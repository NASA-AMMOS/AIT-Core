#!/usr/bin/env python
'''
usage: bliss-seq-encode oco3_seq_SSS_NNN_desc.txt 

Encodes the given relative time command sequence to binary.

Examples:

  $ bliss-seq-encode seq/oco3_seq_gps_001_reset.txt 
'''

import os
import sys
import argparse

from bliss.core import gds, log, seq


def main():
    log.begin()

    defaults      = { }
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('filename',default=None)
    args = vars(parser.parse_args())

    if len(args) == 0:
        stream = open(sys.argv[0])
        for line in stream.readlines():
            if line.startswith('##'): print line.replace('##',''),
        stream.close()
        sys.exit(2)

    filename  = os.path.abspath(args['filename'])
    extension = os.path.splitext(filename)[1]

    if extension.lower() != '.txt':
        log.warn("Filename '%s' does not have a '.txt' extension", filename)

    sequence = seq.Seq(filename)

    if not sequence.validate():
        for msg in sequence.log.messages:
            log.error(msg)
    else:
        binpath = sequence.binpath
        seqid   = sequence.seqid

        log.info("Writing %s (seqid=0x%04x).", binpath, seqid)
        sequence.writeBinary()

    log.end()


if __name__ == '__main__':
    main()
