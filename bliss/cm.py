# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS Configuration Management

The bliss.cm module handles the configuration management
for the GDS including creating and monitoring the GDS
operations directories, data ingestion, and data processing.
"""

import bliss
import yaml
import os
import datetime
import errno


class CMConfig(object):
    '''Configuration Management Config

    Maintains the configuration management configuration
    '''
    def __init__(self, filename=None, datetime=None):
        try:
            if filename is None:
                self.filename = bliss.config.cm.filename
            else:
                self.filename = filename

            self.datetime = datetime

            self.config = self.load(self.filename)

            self.paths = self.config['paths']
        except IOError, e:
            msg = "Could not load YAML '%s': '%s'"
            bliss.log.error(msg, filename, str(e))

    def load(self, filename):
        if self.filename is None:
            self.filename = filename

        with open(self.filename, 'rb') as stream:
            out = yaml.load(stream)

        return out

    @property
    def datetime(self):
        return self._datetime

    @datetime.setter
    def datetime(self, value):
        self._datetime = None
        if value is not None:
            # check value meets our format
            try:
                datetime.datetime.strptime(value, bliss.dmc.DOY_Format)
                self._datetime = value
            except ValueError:
                bliss.log.error("Invalid datetime. Defaulting to TODAY")

        if self._datetime is None:
            self._datetime = bliss.dmc.getUTCDatetimeDOY()

        dtime = self._datetime.split(':')
        self._year = dtime[0]
        self._day = dtime[1]

    @property
    def paths(self):
        return self._paths

    @paths.setter
    def paths(self, value):
        self._paths = {}
        if value is not None:
            # loop through and replace the YYYY and DDD
            # for the year and day, respectively
            for k, v in value.items():
                self._paths[k] = v.replace('YYYY', self._year).replace('DDD', self._day)


# TODO
# def getDefaultSchema():
#     return os.path.join(bliss.config._directory, 'cm_schema.json')


def getDefaultDict(reload=False):
    return bliss.util.getDefaultDict(__name__, 'cm', CMConfig, reload)


def getDefaultDictFilename():
    return bliss.config.cm.filename


def getPath(key, filename=None, datetime=None):
    '''Returns the filepath of the key specified

    Can be used by processor applications to determine default
    output paths
    '''
    try:
        return CMConfig(filename=filename, datetime=datetime).paths[key]
    except Exception:
        bliss.log.error('"%s" does not exist in %s' % (key, getDefaultDictFilename()))
        return None


def createDirStruct(filename=None, datetime=None):
    '''Loops through the paths in the CM config and creates all of the
    directories.

    Replaces YYYY and DDD with the respective year and day-of-year.
    If neither are given as arguments, current UTC day and year are used.
    '''
    config = CMConfig(filename=filename, datetime=datetime)
    for k, path in config.paths.items():
        try:
            os.makedirs(path)
        except OSError, e:
            if e.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    return True
