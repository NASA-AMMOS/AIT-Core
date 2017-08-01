#!/usr/bin/env python
'''
usage: bliss-seq-send [options] filename.rts

Sends the given relative timed sequence via UDP.

--port=number    Port on which to send data  (default: 3075)
--verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-seq-send test.rts
'''

import os
import sys
import socket
import time
import argparse

from bliss.core import cmd, gds, log, seq, util


def system (command):
    log.info('Executing: %s' % command)
    os.system(command)


def main ():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('filename', default=None)
    parser.add_argument('--port', default=3075, type=int)
    parser.add_argument('--verbose', default=0, type=int)

    args = vars(parser.parse_args())

    host     = '127.0.0.1'
    port     = args['port']
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data     = ' '.join(args)
    verbose  = args['verbose']

    cmddict  = cmd.getDefaultCmdDict()
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
                    command  = cmddict.create(name, *args)
                    messages = [ ]

                    time.sleep(delay)
                    log.info(line)

                    if command is None:
                        log.error('unrecognized command: %s' % name)
                    elif command.validate(messages):
                        sock.sendto(command.encode(), (host, port))
                    else:
                        msg = 'Command validation error: %s'
                        log.error(msg, ' '.join(messages))

    except socket.error, err:
        log.error( str(err) )

    except IOError:
        log.error("Could not open '%s' for reading." % filename)

    log.end()

if __name__ == '__main__':
    main()
