#!/usr/bin/env python
'''
usage: bliss-cmd-send [options] command arg1 ... argN

Sends the given command and its arguments to the ISS
simulator via UDP.

  --port=number    Port on which to send data  (default: 3075)
  --verbose=0|1    Hexdump data                (default:    0)

Examples:

  $ bliss-cmd-send OCO3_CMD_START_SEQUENCE_NOW 1
'''


import sys
import socket
import time
import argparse

from bliss.core import cmd, gds, log, util


def main():
    log.begin()

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('command')
    parser.add_argument('arguments', metavar='argument', nargs='*', help='command arguments')
    # parser.add_argument('argument', type=int, default="", action='append')
    parser.add_argument('--port', type=int, default=3075)
    parser.add_argument('--verbose', type=int, default=0)

    args = vars(parser.parse_args())

    host     = "127.0.0.1"
    port     = args['port']
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose  = args['verbose']
    cmddict  = cmd.getDefaultCmdDict()

    if cmddict is not None:
        name     = args['command']
        cmdargs  = args['arguments']
        command  = cmddict.create(name, *cmdargs)
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
