#!/usr/bin/env python

import argparse

from ait.core import log, pcap


"""Query all commands from a Command History PCAP"""


def main():
    log.begin()

    arguments = {
        "filename": {
            "metavar": "</path/to/cmdhist.pcap>",
            "help": "command history pcap",
        }
    }

    ap = argparse.ArgumentParser(description=__doc__)
    for name, params in arguments.items():
        ap.add_argument(name, **params)

    args = ap.parse_args()

    with pcap.open(args.filename) as stream:
        for header, data in stream:
            print(header.timestamp.strftime("%Y-%m-%d %H:%M:%S") + "\t" + data.decode())

    log.end()


if __name__ == "__main__":
    main()
