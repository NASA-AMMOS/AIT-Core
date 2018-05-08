#!/usr/bin/env python

import datetime
import sys

from ait.core import gds,log, pcap

def main():
    log.begin()

    description     = """

    Query all commands from a Command History PCAP

          """

    arguments = {}
    arguments['filename'] = {
        'type'    : str,
        'metavar' : '</path/to/cmdhist.pcap>',
        'help'    : 'command history pcap'
    }

    args = gds.arg_parse(arguments, description)

    with pcap.open(args.filename) as stream:
        for header, data in stream:
            print header.timestamp.strftime('%Y-%m-%d %H:%M:%S') + '\t' + data

    log.end()

if __name__ == "__main__":
    main()
