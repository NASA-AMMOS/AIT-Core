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

import cfg
import log


def deprecated(message):
  def deprecated_decorator(func):
      def deprecated_func(*args, **kwargs):
          log.warn("{} is a deprecated function. {}".format(func.__name__, message))
          return func(*args, **kwargs)
      return deprecated_func
  return deprecated_decorator

sys.modules['ait'].deprecated = deprecated
sys.modules['ait'].DEFAULT_CMD_PORT = 3075
