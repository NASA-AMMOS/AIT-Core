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
usage: ait-seq-send [options] filename.rts

Sends the given relative timed sequence via UDP.

--port=number    Port on which to send data  (default: 3075)
--verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ ait-seq-send test.rts
'''

import os
import sys
import time
import argparse

import ait.core
from ait.core import api, gds, log, seq, util


def system (command):
    log.info('Executing: %s' % command)
    os.system(command)


def main ():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add required command line argument
    parser.add_argument('filename', default=None)

    # Add optional command line arguments
    parser.add_argument(
        '--port',
        default=ait.config.get('command.port', ait.DEFAULT_CMD_PORT),
        type=int
    )
    parser.add_argument('--verbose', default=0, type=int)

    # Get command line arguments
    args = vars(parser.parse_args())

    host     = '127.0.0.1'
    port     = args['port']
    data     = ' '.join(args)
    verbose  = args['verbose']

    cmd = api.CmdAPI(port, verbose=verbose)
    filename = args['filename']

    try:
        with open(filename, 'r') as stream:
            for line in stream.readlines():
                line = line.strip()

                # Skip blank lines and comments
                if len(line) == 0 or line.startswith('#'):
                    continue

                # Meta-command
                elif line.startswith('%'):
                    command = line[1:].strip()
                    system(command)

                # Sequence command
                else:
                    tokens   = line.split()
                    delay    = float(tokens[0])
                    name     = tokens[1]
                    args     = [ util.toNumber(t, t) for t in tokens[2:] ]
                    time.sleep(delay)
                    log.info(line)
                    cmd.send(name, *args)
    except IOError:
        log.error("Could not open '%s' for reading." % filename)

    log.end()

if __name__ == '__main__':
    main()
