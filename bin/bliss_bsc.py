#!/usr/bin/env python

'''
Usage: bliss_bsc.py

Start the bliss BSC for capturing network traffic into PCAP files
and the manager server for RESTful manipulation of active loggers.
'''

import os
import threading
import yaml

import bliss
from bliss.core import bsc


config_file = bliss.config.bsc.filename

def main():
    if not os.path.isfile(config_file):
        print "Unable to locate config. Starting up handlers with default values ..."
        host = 'localhost'
        port = '8080'
        handler_configs = []
        root_log_dir = '/tmp'
        mngr_conf = {
            'root_log_directory': root_log_dir
        }

    else:
        with open(config_file) as log_conf:
            conf = yaml.load(log_conf)

        mngr_conf = conf['capture_manager']
        host = mngr_conf['manager_server']['host']
        port = mngr_conf['manager_server']['port']

        handler_configs = []
        for handler_conf in conf['handlers']:
            if 'path' in handler_conf:
                handler_path = handler_conf.pop('path')
                if not os.path.isabs(handler_path):
                    handler_path = os.path.join(mngr_conf['root_log_directory'], handler_path)
            else:
                handler_path = mngr_conf['root_log_directory']

            handler_configs.append((
                handler_conf.pop('name'),
                handler_conf.pop('address'),
                handler_conf.pop('conn_type'),
                handler_path,
                handler_conf
            ))

    lgr_mngr = bsc.StreamCaptureManager(mngr_conf, handler_configs)
    manager_server = bsc.StreamCaptureManagerServer(logger_manager=lgr_mngr, host=host, port=port)

    t = threading.Thread(target=manager_server.start)
    t.setDaemon(True)
    t.start()

    lgr_mngr.run_socket_event_loop()

if __name__ == '__main__':
    main()
