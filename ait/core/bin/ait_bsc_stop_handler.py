#!/usr/bin/env python

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2016, by the California Institute of Technology. ALL RIGHTS
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
Usage:
    ait-bsc-stop-handler [options] <name>

--service-host=<host> The host for the BSC REST service connection
                      [default: localhost]
--service-port=<port> The port for the BSC REST service connection
                      [default: 8080]
'''

import requests
import argparse


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add required command line arguments
    parser.add_argument('name')

    # Add optional command line arguments
    parser.add_argument('--service-host', default='localhost')
    parser.add_argument('--service-port', type=int, default=8080)

    # Get command line arguments
    args = vars(parser.parse_args())

    host = args['service_host']
    port = args['service_port']

    handler_name = args['name']

    requests.delete('http://{}:{}/{}/stop'.format(host, port, handler_name))

if __name__ == '__main__':
    main()
