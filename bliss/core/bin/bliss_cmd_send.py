#!/usr/bin/env python
'''
bliss-cmd-send
'''


import sys
import socket
import time
import argparse
from collections import OrderedDict

from bliss.core import cmd, gds, log, util


def main():
    log.begin()

    description     = """

    Sends the given command and its arguments to the ISS simulator via UDP.

        Examples:
            $ bliss-cmd-send OCO3_CMD_START_SEQUENCE_NOW 1

          """

    arguments = OrderedDict({
        '--port': {
            'type'    : int,
            'default' : 3075,
            'help'    : 'Port on which to send data'
        },
        '--verbose': {
            'action'  : 'store_true',
            'default' : False,
            'help'    : 'Hexdump of the raw command being sent.'
        }
    })

    arguments['command'] = {
        'type' : str,
        'help' : 'Name of the command to send.'
    }

    arguments['arguments'] = {
        'type'      : util.toNumberOrStr,
        'metavar'   : 'argument',
        'nargs'     : '*',
        'help'      : 'Command arguments.'
    }

    args = gds.arg_parse(arguments, description)

    host     = "127.0.0.1"
    port     = args.port
    sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    verbose  = args.verbose
    cmddict  = cmd.getDefaultCmdDict()

    if cmddict is not None:
        name     = args.command
        cmdargs  = args.arguments
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
