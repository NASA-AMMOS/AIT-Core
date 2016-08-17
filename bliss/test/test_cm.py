# Copyright 2016 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

''''''

import bliss
import os
import datetime


class TestCMConfig(object):
    test_yaml_file = '/tmp/test.yaml'
    # def test_yamlprocess_init(self):
    #     yp = bliss.val.YAMLProcessor()
    #     assert yp.loaded == False
    #     assert yp.data == []
    #     assert yp.doclines == []
    #     assert yp._clean
    #     assert yp.ymlfile is None

    # @mock.patch('bliss.val.YAMLProcessor.load')
    # def test_ymlfile_setter(self, yaml_load_mock):
    #     yp = bliss.val.YAMLProcessor()
    #     assert yaml_load_mock.call_count == 0
    #     yp.ymlfile = 'something that is not None'
    #     assert yaml_load_mock.call_count == 1

    # @mock.patch('bliss.val.YAMLProcessor.process')
    # def test_yaml_load_with_clean(self, process_mock):
    #     yp = bliss.val.YAMLProcessor()
    #     yp.load()
    #     assert process_mock.called
    #     assert yp.loaded

    def test_cmconfig_init(self):
        yaml_doc = (
            'paths:\n'
            '    a: /tmp/foo\n'
            '    b: /tmp/bar\n'
        )

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        cm = bliss.cm.CMConfig(self.test_yaml_file)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == '/tmp/foo'
        assert cm.paths['b'] == '/tmp/bar'

        os.remove(self.test_yaml_file)

    def test_cmconfig_paths_DOY(self):
        yaml_doc = (
            'paths:\n'
            '    a: /tmp/YYYY/DDD/foo\n'
            '    b: /tmp/YYYY/DDD/bar\n'
        )

        # get today's day and year
        timestamp = datetime.datetime.utcnow().timetuple()
        year = timestamp.tm_year
        day = timestamp.tm_yday

        exp_a = '/tmp/%i/%i/foo' % (year, day)
        exp_b = '/tmp/%i/%i/bar' % (year, day)

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        cm = bliss.cm.CMConfig(self.test_yaml_file)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == exp_a
        assert cm.paths['b'] == exp_b

        os.remove(self.test_yaml_file)

    def test_cmconfig_w_input_date(self):
        yaml_doc = (
            'paths:\n'
            '    a: /tmp/YYYY/DDD/foo\n'
            '    b: /tmp/YYYY/DDD/bar\n'
        )

        # get today's day and year
        year = '2016'
        day = '001'
        timestamp = '%s:%s:12:12:01' % (year, day)

        exp_a = '/tmp/%s/%s/foo' % (year, day)
        exp_b = '/tmp/%s/%s/bar' % (year, day)

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        cm = bliss.cm.CMConfig(filename=self.test_yaml_file, datetime=timestamp)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == exp_a
        assert cm.paths['b'] == exp_b

        os.remove(self.test_yaml_file)

    def test_cmconfig_w_bad_input_date(self):
        yaml_doc = (
            'paths:\n'
            '    a: /tmp/YYYY/DDD/foo\n'
            '    b: /tmp/YYYY/DDD/bar\n'
        )

        # get today's day and year
        timestamp = datetime.datetime.utcnow().timetuple()
        year = timestamp.tm_year
        day = timestamp.tm_yday

        exp_a = '/tmp/%i/%i/foo' % (year, day)
        exp_b = '/tmp/%i/%i/bar' % (year, day)

        test_year = '2016'
        test_day = '400'
        test_timestamp = '%s:%s:12:12:01' % (test_year, test_day)

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        cm = bliss.cm.CMConfig(filename=self.test_yaml_file, datetime=test_timestamp)
        assert len(cm.paths) == 2
        assert cm.paths['a'] == exp_a
        assert cm.paths['b'] == exp_b

        os.remove(self.test_yaml_file)

    def test_getPath(self):
        yaml_doc = (
            'paths:\n'
            '    a: /tmp/foo\n'
            '    b: /tmp/bar\n'
        )

        exp_a = '/tmp/foo'
        exp_b = '/tmp/bar'

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        patha = bliss.cm.getPath('a', filename=self.test_yaml_file)
        pathb = bliss.cm.getPath('b', filename=self.test_yaml_file)

        assert patha == exp_a
        assert pathb == exp_b

        os.remove(self.test_yaml_file)

    def test_createDirStruct(self):
        yaml_doc = (
            'paths:\n'
            '    a: /tmp/foo\n'
            '    b: /tmp/bar\n'
        )

        patha = '/tmp/foo'
        pathb = '/tmp/bar'

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_doc)

        out = bliss.cm.createDirStruct(filename=self.test_yaml_file)

        assert out
        assert os.path.isdir(patha)
        assert os.path.isdir(pathb)

        os.remove(self.test_yaml_file)
        os.rmdir(patha)
        os.rmdir(pathb)

if __name__ == '__main__':
    bliss.log.begin()
    nose.main()
    bliss.log.end()
