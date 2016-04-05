"""
BLISS EVR Reader (EVR)

The bliss.evr module is used to read the EVRs from a YAML file.

Also includes deprecated EVRParser class for parsing the EVR
information from the FSW EVR classes.

"""

"""
Authors: Ben Bornstein, Jordan Padams

Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
U.S. Government Sponsorship acknowledged.
"""

import cPickle
import os
import re
import yaml

import bliss


EVR_YAML = bliss.Config.EVR.filename


class EVRReader(object):
    """EVRReader

    Reads in the raw EVR YAML file. Differing from the CMD and TLM
    dictionaries, this reader does not add any processing layers to
    the read.
    """
    def __init__(self, filename=None):
        try:
            if filename is None:
                self.filename = EVR_YAML
            else:
                self.filename = filename

            self.evrs = self.read(self.filename)

        except IOError, e:
            msg = "Could not load EVR YAML '%s': '%s'"
            bliss.log.error(msg, filename, str(e))

    def read(self, filename):
        if self.filename is None:
            self.filename = filename

        with open(self.filename, 'rb') as stream:
            out = yaml.load(stream)

        return out


class DictCache(object):
    def __init__(self, filename=None):
        if filename is None:
            filename = EVR_YAML

        self.filename = filename
        self.pcklname = os.path.splitext(filename)[0] + '.pkl'
        self.reader = None

    def dirty(self):
        return (not os.path.exists(self.pcklname) or
            os.path.getmtime(self.filename) > os.path.getmtime(self.pcklname))

    def load(self):
        if self.reader is None:
            if self.dirty():
                self.reader = EVRReader(self.filename)
                self.update()
            else:
                with open(self.pcklname, "rb") as stream:
                    self.reader = cPickle.load(stream)

        return self.reader

    def update(self):
        msg = "Saving updates from more recent '%s' to '%s'"
        bliss.log.info(msg, self.filename, self.pcklname)
        with open(self.pcklname, "wb") as output:
            cPickle.dump(self.reader, output, -1)


_DefaultDictCache = DictCache()


def getDefaultEVRs():
    """Create a new EVRs object and return the EVRs dictionary"""
    dfltdict = None

    try:
        filename = _DefaultDictCache.filename
        reader   = _DefaultDictCache.load()
    except IOError, e:
        msg = "Could not load default EVR dictionary '%s': %s'"
        bliss.log.error(msg, filename, str(e))

    return reader.evrs
