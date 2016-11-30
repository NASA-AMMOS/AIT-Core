# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Event Record (EVR) Reader

The bliss.core.evr module is used to read the EVRs from a YAML file.

Also includes deprecated EVRParser class for parsing the EVR
information from the FSW EVR classes.

"""

import os
import re
import yaml

import bliss
from bliss.core import log, util


class EVRReader(object):
    """EVRReader

    Reads in the raw EVR YAML file. Differing from the CMD and TLM
    dictionaries, this reader does not add any processing layers to
    the read.
    """
    def __init__(self, filename=None):
        try:
            if filename is None:
                self.filename = bliss.config.evrdict.filename
            else:
                self.filename = filename

            self.evrs = self.read(self.filename)

        except IOError, e:
            msg = "Could not load EVR YAML '%s': '%s'"
            log.error(msg, filename, str(e))

    def read(self, filename):
        if self.filename is None:
            self.filename = filename

        with open(self.filename, 'rb') as stream:
            out = yaml.load(stream)

        return out


def getDefaultSchema():
    return os.path.join(bliss.config._directory, 'evr_schema.json')

def getDefaultDict(reload=False):
    d = util.getDefaultDict(__name__, 'evrdict', EVRReader, reload)
    return d.evrs

def getDefaultEVRs():
    return getDefaultDict()

def getDefaultDictFilename():
    return bliss.config.evrdict.filename
