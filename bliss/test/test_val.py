import os

import bliss
import mock
import nose

class TestYAMLProcessor(object):
    def test_yamlprocess_init(self):
        yp = bliss.val.YAMLProcessor()
        assert yp.loaded == False
        assert yp.data == []
        assert yp.doclines == []
        assert yp._clean
        assert yp.ymlfile is None

    @mock.patch('bliss.val.YAMLProcessor.load')
    def test_ymlfile_setter(self, yaml_load_mock):
        yp = bliss.val.YAMLProcessor()
        assert yaml_load_mock.call_count == 0 
        yp.ymlfile = 'something that is not None'
        assert yaml_load_mock.call_count == 1 

    @mock.patch('bliss.val.YAMLProcessor.process')
    def test_yaml_load_with_clean(self, process_mock):
        yp = bliss.val.YAMLProcessor()
        yp.load()
        assert process_mock.called
        assert yp.loaded

    def test_yaml_load_without_clean(self):
        yaml_docs = (
            '---\n'
            'a: hello\n'
            '---\n'
            'b: goodbye\n'
        )

        with open('/tmp/test.yaml', 'wb') as out:
            out.write(yaml_docs)

        yp = bliss.val.YAMLProcessor(clean=False)
        yp.load('/tmp/test.yaml')
        assert len(yp.data) == 2
        assert yp.data[0]['a'] == 'hello'
        assert yp.data[1]['b'] == 'goodbye'

        os.remove('/tmp/test.yaml')

    def test_invalid_yaml_load(self):
        yaml_docs = """
        ---
        a: these newlines and white space break stuff
        ---
        b: processing wont even get here
        """
        with open('/tmp/test.yaml', 'wb') as out:
            out.write(yaml_docs)

        yp = bliss.val.YAMLProcessor(clean=False)
        nose.tools.assert_raises(
            bliss.val.YAMLError,
            yp.load, '/tmp/test.yaml'
        )

        os.remove('/tmp/test.yaml')

    def test_basic_process_doc_object_name_strip(self):
        yaml_docs = (
            'a: hello\n'
            '--- !foo\n'
            'b: goodbye\n'
        )

        with open('/tmp/test.yaml', 'w') as out:
            out.write(yaml_docs)

        yp = bliss.val.YAMLProcessor(clean=False)
        out = yp.process('/tmp/test.yaml')

        assert len(yp.doclines) == 2
        assert yp.doclines == [1, 3]
        assert '!foo' not in out

    def test_basic_process_seq_name_strip(self):
        yaml_docs = (
            ' - !bar\n'
            ' - blah\n'
        )

        with open('/tmp/test.yaml', 'w') as out:
            out.write(yaml_docs)

        yp = bliss.val.YAMLProcessor(clean=False)
        out = yp.process('/tmp/test.yaml')

        assert "bar:" in out

    def test_empty_file_process(self):
        open('/tmp/test.yaml', 'w').close()

        yp = bliss.val.YAMLProcessor(clean=False)
        nose.tools.assert_raises(
            bliss.val.YAMLError,
            yp.process, '/tmp/test.yaml'
        )

    def test_invalid_yaml_process(self):
        yaml_docs = """
        ---
        a: these newlines and white space break stuff
        ---
        b: processing wont even get here
        """
        open('/tmp/test.yaml', 'w').close()

        yp = bliss.val.YAMLProcessor(clean=False)
        nose.tools.assert_raises(
            IOError,
            yp.process, '/tmp/thisFileDoesntExistAndWillCauseAnError'
        )

if __name__ == '__main__':
    nose.main()
