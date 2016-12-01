#!/usr/bin/env python

'''
Usage:
    bliss_bsc_create_handler.py [options] <name> <loc> <port> <conn_type>

--service-host=<host> The host for the BSC REST service connection
                      [default: localhost]
--service-port=<port> The port for the BSC REST service connection
                      [default: 8080]
--rotate=<rl>         Flag saying whether the log should be rotated
                      automatically [default: True]
--rotate-index=<rli>  If log rotation is enabled, this determines the
                      frequency of a rotation. One of 'year', 'month',
                      'day', 'hour', 'minutes', 'second' [default: day]
--rotate-delta=<rld>  If log rotation is enabled, this determines the
                      delta between log creation and current time
                      rotate-index value needed to trigger a log
                      rotation [default: 1]
--file-pattern=<fnp>  The file pattern for the log file name. This can
                      include handler metadata values as well as strftime
                      format characters [default: %Y-%m-%d-%H-%M-%S-{name}.pcap]
'''

from docopt import docopt
import requests


if __name__ == '__main__':
    arguments = docopt(__doc__)

    host = arguments.pop('--service-host')
    port = arguments.pop('--service-port')

    handler_name = arguments.pop('<name>')

    handler_port = arguments.pop('<port>')
    arguments['port'] = handler_port

    handler_conn_type = arguments.pop('<conn_type>')
    arguments['conn_type'] = handler_conn_type

    handler_loc = arguments.pop('<loc>')
    arguments['loc'] = handler_loc

    arguments['rotate_log'] = eval(arguments.pop('--rotate'))
    arguments['rotate_log_index'] = arguments.pop('--rotate-index')
    arguments['rotate_log_delta'] = arguments.pop('--rotate-delta')
    arguments['file_name_pattern'] = arguments.pop('--file-pattern')

    requests.post(
        'http://{}:{}/{}/start'.format(host, port, handler_name),
        data=arguments
    )
