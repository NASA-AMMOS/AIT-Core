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

#
#
#    Sends the given command and its arguments to the ISS simulator via
#    the AIT server, or if the 'udp' flag is set then directly via UDP.
#
#        Examples:
#            $ ait-cmd-send OCO3_CMD_START_SEQUENCE_NOW 1
#
#

"""
usage: ait-cmd-send [options] command [arguments]

Sends the given command and its arguments to the ISS simulator via
the AIT server, or if the 'udp' flag is set then directly via UDP.

--verbose          Hexdump data                  (default: False)
--topic=topicname  Sets the name of ZMQ topic    (default: '__commands__')
--udp              Send data via UDP             (default: False)
--host=url         URL of the host to send data  (default: '127.0.0.1')
--port=number      Port on which to send data    (default: 3075)

Examples:

  $ ait-cmd-send OCO3_CMD_START_SEQUENCE_NOW 1
"""

import argparse
from collections import OrderedDict

import ait
from ait.core import api, log, util


def main():
    log.begin()

    descr = (
        "Sends the given command and its arguments to the ISS simulator via  "
        "the AIT server, or if the 'udp' flag is set then directly via UDP."
    )

    parser = argparse.ArgumentParser(
        description=descr, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    arg_defns = OrderedDict(
        {
            "--topic": {
                "type": str,
                "default": ait.config.get("command.topic", ait.DEFAULT_CMD_TOPIC),
                "help": "Name of topic from which to publish data",
            },
            "--verbose": {
                "action": "store_true",
                "default": False,
                "help": "Hexdump of the raw command being sent.",
            },
            "--udp": {
                "action": "store_true",
                "default": False,
                "help": "Send data to UDP socket.",
            },
            "--host": {
                "type": str,
                "default": ait.DEFAULT_CMD_HOST,
                "help": "Host to which to send data",
            },
            "--port": {
                "type": int,
                "default": ait.config.get("command.port", ait.DEFAULT_CMD_PORT),
                "help": "Port on which to send data",
            },
        }
    )

    arg_defns["command"] = {"type": str, "help": "Name of the command to send."}

    arg_defns["arguments"] = {
        "type": util.toNumberOrStr,
        "metavar": "arguments",
        "nargs": "*",
        "help": "Command arguments.",
    }

    # Push argument defs to the parser
    for name, params in arg_defns.items():
        parser.add_argument(name, **params)

    # Get arg results of the parser
    args = parser.parse_args()

    # Extract args to local fields
    host = args.host
    port = args.port
    verbose = args.verbose
    udp = args.udp
    topic = args.topic

    # If UDP enabled, collect host/port info
    if udp:
        if host is not None:
            dest = (host, port)
        else:
            dest = port

        cmd_api = api.CmdAPI(udp_dest=dest, verbose=verbose)
    # Default CmdAPI connect hooks up to C&DH server 0MQ port
    else:
        cmd_api = api.CmdAPI(verbose=verbose, cmdtopic=topic)

    cmd_args = cmd_api.parse_args(args.command, *args.arguments)

    cmd_api.send(args.command, *cmd_args)

    log.end()


if __name__ == "__main__":
    main()
