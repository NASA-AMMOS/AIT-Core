#!/usr/bin/env python
#
# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS EVR Parser Tests

Provides unit and functional tests for the bliss.evr module.
"""

import sys
import os
import datetime

import nose
import bliss


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
            path:    bin/bliss-orbits
            rtaddr:  15

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
    prefix   = os.path.join('/', 'bliss')
    actual   = {
        'desc'    : 'Test bliss.cfg.expandConfigPaths()',
        'file'    : os.path.join('bin', 'bliss-orbits'),
        'filename': os.path.join('bin', 'bliss-orbits'),
        'nested'  : {
            'desc'    : 'Test expansion of nested dictionaries too',
            'file'    : os.path.join('bin', 'bliss-cmd-send'),
            'filename': os.path.join('bin', 'bliss-cmd-send'),
        }
    }
    expected = {
        'desc'    : 'Test bliss.cfg.expandConfigPaths()',
        'file'    : os.path.join(prefix, 'bin', 'bliss-orbits'),
        'filename': os.path.join(prefix, 'bin', 'bliss-orbits'),
        'nested'  : {
            'desc'    : 'Test expansion of nested dictionaries too',
            'file'    : os.path.join(prefix, 'bin', 'bliss-cmd-send'),
            'filename': os.path.join(prefix, 'bin', 'bliss-cmd-send'),
        }
    }

    bliss.cfg.expandConfigPaths(actual, prefix, None, 'file', 'filename')
    assert actual == expected

def test_expandConfigPaths_w_variables ():
    prefix   = os.path.join('/', 'bliss')
    pathvars = {
        'x': 'test-x',
        'y': 'test-y',
        'hostname': hostname()
    }
    actual   = {
        'desc'    : 'Test bliss.cfg.expandConfigPaths() with variables',
        'file'    : os.path.join('bin', '${x}', 'bliss-orbits'),
        'filename': os.path.join('bin', '${y}', 'bliss-orbits')
    }
    expected = {
        'desc'    : 'Test bliss.cfg.expandConfigPaths() with variables',
        'file'    : os.path.join(prefix, 'bin', 'test-x', 'bliss-orbits'),
        'filename': os.path.join(prefix, 'bin', 'test-y', 'bliss-orbits')
    }

    bliss.cfg.expandConfigPaths(actual, prefix, pathvars, 'file', 'filename')
    assert actual == expected


def test_expandPath ():
    pathname = os.path.join('~', 'bin', 'bliss-orbits')
    assert bliss.cfg.expandPath(pathname) == os.path.expanduser(pathname)

    pathname = os.path.join('/', 'bin', 'bliss-orbits')
    assert bliss.cfg.expandPath(pathname) == pathname

    pathname = os.path.join('' , 'bin', 'bliss-orbits')
    assert bliss.cfg.expandPath(pathname) == os.path.abspath(pathname)

    pathname = os.path.join('' , 'bin', 'bliss-orbits')
    prefix   = os.path.join('/', 'bliss')
    expected = os.path.join(prefix, pathname)
    assert bliss.cfg.expandPath(pathname, prefix) == expected


def test_replaceVariables ():
    # Test expandPath with simple custom path variable
    pathvars = {
        'x' : 'test'
    }
    pathname = os.path.join('/' , '${x}', 'bliss-orbits')
    expected = [ os.path.join('/', pathvars['x'], 'bliss-orbits') ]
    assert bliss.cfg.replaceVariables(pathname, pathvars) == expected

    # Test expandPath with more complex path variable with multiple
    # permutations
    pathvars = {
        'x' : 'x1',
        'y' : ['y1', 'y2'],
        'z' : ['z1', 'z2']
    }
    pathname = os.path.join('/' , '${x}', '${y}', '${z}','bliss-orbits')
    expected = [
        os.path.join('/', pathvars['x'], pathvars['y'][0],
                     pathvars['z'][0], 'bliss-orbits'),
        os.path.join('/', pathvars['x'], pathvars['y'][0],
                     pathvars['z'][1], 'bliss-orbits'),
        os.path.join('/', pathvars['x'], pathvars['y'][1],
                     pathvars['z'][0], 'bliss-orbits'),
        os.path.join('/', pathvars['x'], pathvars['y'][1],
                     pathvars['z'][1], 'bliss-orbits')
    ]
    assert bliss.cfg.replaceVariables(pathname, pathvars) == expected

def test_addPathVariables ():
    config = bliss.cfg.BlissConfig(data=YAML())
    before = config.pathvars
    before_len = len(before.keys())

    pathvars = {
        'x': 'test-x',
        'y': 'test-y'
    }
    config.addPathVariables(pathvars)
    after = config.pathvars
    after_len = len(after.keys())

    assert before_len < after_len
    assert 'x' in after.keys()
    assert 'y' in after.keys()

def test_flatten ():
    d = { 'a': { 'foo': 'a' }, 'b': { 'foo': 'b' } }
    assert bliss.cfg.flatten(dict(d), 'a', 'b') == { 'foo': 'b' }
    assert bliss.cfg.flatten(dict(d), 'b', 'a') == { 'foo': 'a' }


def test_loadYAML ():
    with TestFile(data=YAML()) as filename:
        assert bliss.cfg.loadYAML(filename) == bliss.cfg.loadYAML(data=YAML())


def test_merge ():
    d = { 'foo': 'bar' }
    o = { 'foo': 'baz' }
    assert bliss.cfg.merge(d, o) == o

    d = { 'foo': 'bar' }
    o = { 'baz': 'bop' }
    assert bliss.cfg.merge(d, o) == { 'foo': 'bar', 'baz': 'bop' }


def assert_BlissConfig (config, path, filename=None):
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


def test_BlissConfig ():
    config = bliss.cfg.BlissConfig(data=YAML())
    path   = 'bin/bliss-orbits'
    assert_BlissConfig(config, path)

    with TestFile(data=YAML()) as filename:
        config = bliss.cfg.BlissConfig(filename)
        assert_BlissConfig(config, path, filename)

        config.reload()
        assert_BlissConfig(config, path, filename)

if __name__ == '__main__':
    nose.main()
