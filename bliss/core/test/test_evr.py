#!/usr/bin/env python2.7

# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

import nose
import nose.tools

import bliss
from bliss.core import evr


class TestEVRReader(object):
    def test_filename(self):
        reader = evr.EVRReader(filename=evr.getDefaultDictFilename())
        assert reader.filename == evr.getDefaultDictFilename()

    def test_default_filename(self):
        reader = evr.EVRReader()
        assert reader.filename == evr.getDefaultDictFilename()

def test_evr_load():
    evr_dicts = evr.getDefaultDict()
    assert len(evr_dicts) == 4

    count = 1
    for e in evr_dicts:
        assert e.code == count
        count += 1

    assert evr_dicts[0].name == "NO_ERROR"
