# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

''''''

import bliss
import os
import datetime
import nose


class TestCMConfig(object):
    def test_cmconfig_init(self):
        pathdict = {
            'a': '/tmp/foo',
            'b': '/tmp/bar'
        }

        cm = bliss.cm.CMConfig(paths=pathdict)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == '/tmp/foo'
        assert cm.paths['b'] == '/tmp/bar'


    def test_cmconfig_paths_DOY(self):
        pathdict = {
            'a': '/tmp/YYYY/DDD/foo',
            'b': '/tmp/YYYY/DDD/bar'
        }

        # get today's day and year
        timestamp = datetime.datetime.utcnow().timetuple()
        year = timestamp.tm_year
        day = timestamp.tm_yday

        exp_a = '/tmp/%i/%i/foo' % (year, day)
        exp_b = '/tmp/%i/%i/bar' % (year, day)

        cm = bliss.cm.CMConfig(pathdict)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == exp_a
        assert cm.paths['b'] == exp_b


    def test_cmconfig_w_input_date(self):
        pathdict = {
            'a': '/tmp/YYYY/DDD/foo',
            'b': '/tmp/YYYY/DDD/bar'
        }

        # get today's day and year
        year = '2016'
        day = '001'
        timestamp = '%s:%s:12:12:01' % (year, day)

        exp_a = '/tmp/%s/%s/foo' % (year, day)
        exp_b = '/tmp/%s/%s/bar' % (year, day)

        cm = bliss.cm.CMConfig(paths=pathdict, datetime=timestamp)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == exp_a
        assert cm.paths['b'] == exp_b


    def test_cmconfig_w_bad_input_date(self):
        pathdict = {
            'a': '/tmp/YYYY/DDD/foo',
            'b': '/tmp/YYYY/DDD/bar'
        }

        # get today's day and year
        timestamp = datetime.datetime.utcnow().timetuple()
        year = timestamp.tm_year
        day = timestamp.tm_yday

        exp_a = '/tmp/%i/%i/foo' % (year, day)
        exp_b = '/tmp/%i/%i/bar' % (year, day)

        test_year = '2016'
        test_day = '400'
        test_timestamp = '%s:%s:12:12:01' % (test_year, test_day)

        cm = bliss.cm.CMConfig(paths=pathdict, datetime=test_timestamp)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == exp_a
        assert cm.paths['b'] == exp_b


    def test_getPath(self):
        pathdict = {
            'a': '/tmp/foo',
            'b': '/tmp/bar'
        }

        exp_a = '/tmp/foo'
        exp_b = '/tmp/bar'

        patha = bliss.cm.getPath('a', paths=pathdict)
        pathb = bliss.cm.getPath('b', paths=pathdict)

        assert patha == exp_a
        assert pathb == exp_b


    def test_createDirStruct(self):
        pathdict = {
            'a': '/tmp/foo',
            'b': '/tmp/bar'
        }

        patha = '/tmp/foo'
        pathb = '/tmp/bar'

        out = bliss.cm.createDirStruct(paths=pathdict)

        assert out
        assert os.path.isdir(patha)
        assert os.path.isdir(pathb)

        os.rmdir(patha)
        os.rmdir(pathb)

    def test_createDirStruct_cfg(self):
        yaml_doc = (
            'default:\n'
            '    gds_paths:\n'
            '        a: /tmp/foo\n'
            '        b: /tmp/bar\n'
        )

        patha = '/tmp/foo'
        pathb = '/tmp/bar'
        bliss.config.reload(data=yaml_doc)
        out = bliss.cm.createDirStruct()
        assert out
        assert os.path.isdir(patha)
        assert os.path.isdir(pathb)

        bliss.config.reload(filename=bliss.config.getDefaultFilename())
        os.rmdir(patha)
        os.rmdir(pathb)


    def test_createDirStruct_cfg_w_date(self):
        yaml_doc = (
            'default:\n'
            '    gds_paths:\n'
            '        a: /tmp/YYYY/DDD/foo\n'
            '        b: /tmp/YYYY/DDD/bar\n'
        )

        # get today's day and year
        year = '2016'
        day = '001'
        timestamp = '%s:%s:12:12:01' % (year, day)

        exp_a = '/tmp/%s/%s/foo' % (year, day)
        exp_b = '/tmp/%s/%s/bar' % (year, day)

        bliss.config.reload(data=yaml_doc)
        out = bliss.cm.createDirStruct(datetime=timestamp)

        assert out
        assert os.path.isdir(exp_a)
        assert os.path.isdir(exp_b)

        bliss.config.reload(filename=bliss.config.getDefaultFilename())

        os.rmdir(exp_a)
        os.rmdir(exp_b)

if __name__ == '__main__':
    bliss.log.begin()
    nose.main()
    bliss.log.end()
