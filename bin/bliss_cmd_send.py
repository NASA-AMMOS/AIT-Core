#!/usr/bin/env python
'''
usage: bliss-cmd-send.py [options] command arg1 ... argN

Sends the given command and its arguments to the ISS
simulator via UDP.

  --port=number    Port on which to send data  (default: 3075)
  --verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-cmd-send.py OCO3_CMD_START_SEQUENCE_NOW 1
'''


import sys
import socket
import time

from bliss.core import cmd, gds, log, util


def main():
    log.begin()

    defaults      = { "port": 3075, "verbose": 0 }
    options, args = gds.parseArgs(sys.argv[1:], defaults)

    if len(args) == 0:
        gds.usage(exit=True)

    host     = "127.0.0.1"
    port     = options['port']
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose  = options['verbose']
    cmddict  = cmd.getDefaultCmdDict()

    if cmddict is not None:
        name     = args[0]
        args     = [ util.toNumber(t, t) for t in args[1:] ]
        command  = cmddict.create(name, *args)
        messages = [ ]

        if command is None:
            log.error("unrecognized command: %s" % name)
        elif not command.validate(messages):
            for msg in messages:
                log.error(msg)
        else:
            encoded = command.encode()

            if verbose:
                size     = len(command.name)
                pad      = (size - len(command.name) + 1) * " "
                preamble = command.name + ":" + pad
                gds.hexdump(encoded, preamble=preamble)

            try:
                msg = "Sending to %s:%d: %s"
                log.info(msg, host, port, command.name)
                sock.sendto(encoded, (host, port))
            except socket.error, err:
                log.error( str(err) )

    log.end()


if __name__ == '__main__':
    main()
