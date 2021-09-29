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

import sys

# cfg isn't used but we want the AIT-level config attribute created
from ait.core import cfg, log  # noqa


def deprecated(message):
    def deprecated_decorator(func):
        def deprecated_func(*args, **kwargs):
            log.warn("{} is a deprecated function. {}".format(func.__name__, message))
            return func(*args, **kwargs)

        return deprecated_func

    return deprecated_decorator


sys.modules["ait"].deprecated = deprecated  # type: ignore[attr-defined]
sys.modules["ait"].DEFAULT_CMD_PORT = 3075  # type: ignore[attr-defined]
sys.modules["ait"].DEFAULT_CMD_HOST = "127.0.0.1"  # type: ignore[attr-defined]

# Name of the ZMQ topic used to accept commands from external sources
sys.modules["ait"].DEFAULT_CMD_TOPIC = "__commands__"  # type: ignore[attr-defined]

# Name of the ZMQ topic / stream used for making telemetry packets available to the script API
sys.modules["ait"].DEFAULT_TLM_TOPIC = "__tlmpkts__"  # type: ignore[attr-defined]

# Number of seconds to sleep after ZmqSocket.connect() call, affects clients
sys.modules["ait"].DEFAULT_CMD_ZMQ_SLEEP = 1  # type: ignore[attr-defined]


sys.modules["ait"].SERVER_DEFAULT_XSUB_URL = "tcp://*:5559"  # type: ignore[attr-defined]
sys.modules["ait"].SERVER_DEFAULT_XPUB_URL = "tcp://*:5560"  # type: ignore[attr-defined]
