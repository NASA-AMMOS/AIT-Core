#!/usr/bin/env python

"""
Usage: ait-server

Start the AIT telemetry server for managing telemety streams,
command outputs, processing handlers, and plugins.
"""

import argparse

from ait.core.server import Server


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    args = ap.parse_args()  # noqa

    tlm_cmd_serv = Server()
    tlm_cmd_serv.wait()


if __name__ == "__main__":
    main()
