#!/usr/bin/env python

'''
Usage:
    bliss_bsc_stop_handler.py [options] <name>

--service-host=<host> The host for the BSC REST service connection
                      [default: localhost]
--service-port=<port> The port for the BSC REST service connection
                      [default: 8080]
'''

from docopt import docopt
import requests


if __name__ == '__main__':
    arguments = docopt(__doc__)

    host = arguments.pop('--service-host')
    port = arguments.pop('--service-port')

    handler_name = arguments.pop('<name>')

    requests.delete('http://{}:{}/{}/stop'.format(host, port, handler_name))
