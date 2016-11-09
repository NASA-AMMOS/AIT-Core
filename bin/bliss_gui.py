#!/usr/bin/env python

"""
Usage:
  bliss_gui.py [<port> --host=<host> --browser=<browser>]

Options:
  port       GUI client HTTP connections port
  host       GUI client HTTP connections hostname
  browser    GUI client browser to start (may be "none")
"""

import socket
import sys

import docopt
import gevent
import gevent.monkey
import geventwebsocket

gevent.monkey.patch_all()

import bliss

try:
    bliss.log.begin()
    arguments = docopt.docopt(__doc__, version='bliss-gui 0.1.0')
    browser   = arguments['--browser']
    host      = arguments['--host']
    port      = arguments['<port>'] or 8000

    if host is None:
        if sys.platform == 'darwin':
            host = 'localhost'
        else:
            host = socket.gethostname().split('.')[0]

    app = bliss.gui.App
    url = 'http://%s:%d' % (host, port)
    web = gevent.pywsgi.WSGIServer(('0.0.0.0', port), app,
              handler_class=geventwebsocket.handler.WebSocketHandler)

    web.start()
    bliss.gui.startBrowser(url, browser)

    bliss.log.info('Connect to %s' % url)
    bliss.log.info('Ctrl-C to exit')

    gevent.wait()

except KeyboardInterrupt:
    bliss.log.info('Received Ctrl-C.  Stopping BLISS GUI.')
    web.stop()

except Exception as e:
    bliss.log.error('BLISS GUI error: %s' % str(e))

bliss.log.end()
