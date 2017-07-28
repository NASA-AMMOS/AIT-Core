#!/usr/bin/env python
'''
usage: bliss-seq-print oco3_seq_SSS_NNN_desc.bin

Prints the given binary relative time command sequence to standard
output as text.

Examples:

  $ bliss-seq-print seq/oco3_seq_gps_001_reset.bin
'''

import os
import sys
import argparse

from bliss.core import gds, log, seq


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description = __doc__,
        formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('filename')

    args = vars(parser.parse_args())

    filename  = os.path.abspath(args['filename'])
    extension = os.path.splitext(filename)[1]

    if extension.lower() != '.bin':
        log.warn("Filename '%s' does not have a '.bin' extension", filename)

    sequence = seq.Seq(filename)

    if not sequence.validate():
        for msg in sequence.messages:
            log.error(msg)

    sequence.printText()

    log.end()


if __name__ == '__main__':
    main()
