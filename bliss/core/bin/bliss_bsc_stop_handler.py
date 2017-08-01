#!/usr/bin/env python

'''
Usage:
    bliss-bsc-stop-handler [options] <name>

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
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('name')
    parser.add_argument('--service-host', default='localhost')
    parser.add_argument('--service-port', type=int, default=8080)
    
    args = vars(parser.parse_args())

    host = args['service-host']
    port = args['service-port']

    handler_name = args['name']

    requests.delete('http://{}:{}/{}/stop'.format(host, port, handler_name))

if __name__ == '__main__':
    main()
