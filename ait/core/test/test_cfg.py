#!/usr/bin/env python2.7

# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2015, by the California Institute of Technology. ALL RIGHTS
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
import os
import time

import nose

from ait.core import cfg

from . import TestFile


def YAML ():
    """
    # Call YAML() to return the YAML string below, customized for this
    # platform (i.e. OS) and hostname.

    default:
        ISS:
            apiport: 9090
            bticard: 0
            desc:    ISS PL/MDM Simulator
            path:    bin/ait-orbits
            rtaddr:  15

        data:
            test1:
                path: /gds/%Y/%Y-%j/test1
            test2:
                path: /gds/%Y/%Y-%j/test2

    PLATFORM:
        ISS:
            bticard: 6

    HOSTNAME:
        ISS:
            apiport: 1234
    """
    s = YAML.__doc__
    return s.replace('PLATFORM', platform()).replace('HOSTNAME', hostname())


def hostname ():
    import platform
    return platform.node().split('.')[0]


def platform ():
    return sys.platform


def test_expandConfigPaths ():
    prefix   = os.path.join('/', 'ait')
    actual   = {
        'desc'    : 'Test cfg.expandConfigPaths()',
        'file'    : os.path.join('bin', 'ait-orbits'),
        'filename': os.path.join('bin', 'ait-orbits'),
        'nested'  : {
            'desc'    : 'Test expansion of nested dictionaries too',
            'file'    : os.path.join('bin', 'ait-cmd-send'),
            'filename': os.path.join('bin', 'ait-cmd-send'),
        }
    }
    expected = {
        'desc'    : 'Test cfg.expandConfigPaths()',
        'file'    : os.path.join(prefix, 'bin', 'ait-orbits'),
        'filename': os.path.join(prefix, 'bin', 'ait-orbits'),
        'nested'  : {
            'desc'    : 'Test expansion of nested dictionaries too',
            'file'    : os.path.join(prefix, 'bin', 'ait-cmd-send'),
            'filename': os.path.join(prefix, 'bin', 'ait-cmd-send'),
        }
    }

    cfg.expandConfigPaths(actual, prefix, None, None, '', 'file', 'filename')
    assert actual == expected

def test_expandConfigPaths_w_variables ():
    prefix   = os.path.join('/', 'ait')
    pathvars = {
        'x': 'test-x',
        'y': 'test-y',
        'hostname': hostname()
    }
    actual   = {
        'desc'    : 'Test cfg.expandConfigPaths() with variables',
        'file'    : os.path.join('bin', '${x}', 'ait-orbits'),
        'filename': os.path.join('bin', '${y}', 'ait-orbits')
    }
    expected = {
        'desc'    : 'Test cfg.expandConfigPaths() with variables',
        'file'    : os.path.join(prefix, 'bin', 'test-x', 'ait-orbits'),
        'filename': os.path.join(prefix, 'bin', 'test-y', 'ait-orbits')
    }

    cfg.expandConfigPaths(actual, prefix, None, pathvars, '', 'file', 'filename')
    assert actual == expected


def test_replaceVariables ():
    # Test expandPath with simple custom path variable
    pathvars = {
        'x' : 'test'
    }
    pathname = os.path.join('/' , '${x}', 'ait-orbits')
    expected = [ os.path.join('/', pathvars['x'], 'ait-orbits') ]
    assert cfg.replaceVariables(pathname, pathvars=pathvars) == expected

    # Test expandPath with more complex path variable with multiple
    # permutations
    pathvars = {
        'x' : 'x1',
        'y' : ['y1', 'y2'],
        'z' : ['z1', 'z2']
    }
    pathname = os.path.join('/' , '${x}', '${y}', '${z}','ait-orbits')
    expected = [
        os.path.join('/', pathvars['x'], pathvars['y'][0],
                     pathvars['z'][0], 'ait-orbits'),
        os.path.join('/', pathvars['x'], pathvars['y'][0],
                     pathvars['z'][1], 'ait-orbits'),
        os.path.join('/', pathvars['x'], pathvars['y'][1],
                     pathvars['z'][0], 'ait-orbits'),
        os.path.join('/', pathvars['x'], pathvars['y'][1],
                     pathvars['z'][1], 'ait-orbits')
    ]
    assert sorted(cfg.replaceVariables(pathname, pathvars=pathvars)) == sorted(expected)

def test_replaceVariables_strftime ():
    # Test replaceVariables with strftime directives
    pathname = os.path.join('/', '%Y', '%Y-%j', 'ait-orbits')

    expected = [ os.path.join('/', 
        time.strftime('%Y', time.gmtime()),
        time.strftime('%Y-%j', time.gmtime()),
        'ait-orbits') ]

    assert sorted(cfg.replaceVariables(pathname)) == sorted(expected)

def test_replaceVariables_strftime_addday ():
    # Test replaceVariables with strftime directives
    pathname = os.path.join('/', '%Y', '%Y-%j', 'ait-orbits')

    expected = [ os.path.join('/', 
        time.strftime('%Y', time.gmtime()),
        time.strftime('%Y-%j', time.gmtime()),
        'ait-orbits') ]

    assert sorted(cfg.replaceVariables(pathname)) == sorted(expected)

def test_addPathVariables ():
    config = cfg.AitConfig(data=YAML())
    before = config._pathvars
    before_len = len(before.keys())

    pathvars = {
        'x': 'test-x',
        'y': 'test-y'
    }
    config.addPathVariables(pathvars)
    after = config._pathvars
    after_len = len(after.keys())

    assert before_len < after_len
    assert 'x' in after.keys()
    assert 'y' in after.keys()

def test_datapaths ():
    """
    default:
        ISS:
            apiport: 9090
            bticard: 0
            desc:    ISS PL/MDM Simulator
            path:    bin/ait-orbits
            rtaddr:  15

    """
    # check data paths work from YAML()
    config = cfg.AitConfig(data=YAML())
    assert len(config._datapaths) > 0
    
    # check if data paths do not exist
    config = cfg.AitConfig(data=test_datapaths.__doc__)
    try:
        paths = config._datapaths
        assert False
    except cfg.AitConfigMissing as e:
        assert True
        
def test_flatten ():
    d = { 'a': { 'foo': 'a' }, 'b': { 'foo': 'b' } }
    assert cfg.flatten(dict(d), 'a', 'b') == { 'foo': 'b' }
    assert cfg.flatten(dict(d), 'b', 'a') == { 'foo': 'a' }


def test_loadYAML ():
    with TestFile(data=YAML()) as filename:
        assert cfg.loadYAML(filename) == cfg.loadYAML(data=YAML())


def test_merge ():
    d = { 'foo': 'bar' }
    o = { 'foo': 'baz' }
    assert cfg.merge(d, o) == o

    d = { 'foo': 'bar' }
    o = { 'baz': 'bop' }
    assert cfg.merge(d, o) == { 'foo': 'bar', 'baz': 'bop' }


def assert_AitConfig (config, path, filename=None):
    assert config.ISS.apiport == 1234
    assert config.ISS.bticard == 6
    assert config.ISS.desc    == 'ISS PL/MDM Simulator'
    assert config.ISS.path    == os.path.join(config._directory, path)
    assert config.ISS.rtaddr  == 15

    assert config._hostname == hostname()
    assert config._platform == platform()
    assert config._filename == filename

    assert config     != config.ISS
    assert config.ISS == config['ISS']

    year = time.strftime('%Y', time.gmtime())
    doy = time.strftime('%j', time.gmtime())
    base = '/gds/%s/%s-%s/' % (year, year, doy)
    assert config.data.test1.path == base + 'test1'
    assert config.data.test2.path == base + 'test2'

    assert 'foo' not in config
    try:
        config.foo
        assert False
    except AttributeError:
        pass

    try:
        config['foo']
        assert False
    except KeyError:
        pass

    assert type(str(config)) is str


def test_AitConfig ():
    config = cfg.AitConfig(data=YAML())
    path   = 'bin/ait-orbits'
    assert_AitConfig(config, path)

    with TestFile(data=YAML()) as filename:
        config = cfg.AitConfig(filename)
        assert_AitConfig(config, path, filename)

        config.reload()
        assert_AitConfig(config, path, filename)


if __name__ == '__main__':
    nose.main()
