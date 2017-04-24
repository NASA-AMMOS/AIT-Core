#!/usr/bin/env python
'''
usage: bliss_seq_send.py [options] filename.rts

Sends the given relative timed sequence via UDP.

--port=number    Port on which to send data  (default: 3075)
--verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-seq-send.py test.rts
'''

import os
import sys
import socket
import time

from bliss.core import cmd, gds, log, seq, util


def system (command):
    log.info('Executing: %s' % command)
    os.system(command)


def main ():
    log.begin()

    defaults      = { 'port': 3075, 'verbose': 0 }
    options, args = gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
        gds.usage(exit=True)

    host     = '127.0.0.1'
    port     = options['port']
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data     = ' '.join(args)
    verbose  = options['verbose']

    cmddict  = cmd.getDefaultCmdDict()
    filename = args[0]

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
