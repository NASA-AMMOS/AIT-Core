#!/usr/bin/env python2.7

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

import os
import pkg_resources
import jsonschema
import logging

import mock
import nose

import ait
from ait.core import cmd, log, tlm, val, util, evr


DATA_PATH = os.path.join(os.path.dirname(__file__), 'testdata', 'val')


class TestYAMLProcessor(object):
    test_yaml_file = '/tmp/test.yaml'

    def test_yamlprocess_init(self):
        yp = val.YAMLProcessor()
        assert yp.loaded == False
        assert yp.data == []
        assert yp.doclines == []
        assert yp._clean
        assert yp.ymlfile is None

    @mock.patch('ait.core.val.YAMLProcessor.load')
    def test_ymlfile_setter(self, yaml_load_mock):
        yp = val.YAMLProcessor()
        assert yaml_load_mock.call_count == 0
        ymlfile = 'something that is not None'
        yp.load(ymlfile)
        assert yaml_load_mock.call_count == 1

    @mock.patch('ait.core.val.YAMLProcessor.process')
    def test_yaml_load_with_clean(self, process_mock):
        yp = val.YAMLProcessor()
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

        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_docs)

        yp = val.YAMLProcessor(clean=False)
        yp.load(self.test_yaml_file)
        assert len(yp.data) == 2
        assert yp.data[0]['a'] == 'hello'
        assert yp.data[1]['b'] == 'goodbye'

        os.remove(self.test_yaml_file)

    def test_invalid_yaml_load(self):
        yaml_docs = """
        ---
        a: these newlines and white space break stuff
        ---
        b: processing wont even get here
        """
        with open(self.test_yaml_file, 'wb') as out:
            out.write(yaml_docs)

        yp = val.YAMLProcessor(clean=False)
        nose.tools.assert_raises(
            util.YAMLError,
            yp.load, self.test_yaml_file
        )

        os.remove(self.test_yaml_file)

    def test_basic_process_doc_object_name_strip(self):
        yaml_docs = (
            'a: hello\n'
            '--- !foo\n'
            'b: goodbye\n'
        )

        with open(self.test_yaml_file, 'w') as out:
            out.write(yaml_docs)

        yp = val.YAMLProcessor(clean=False)
        out = yp.process(self.test_yaml_file)

        assert len(yp.doclines) == 2
        assert yp.doclines == [1, 3]
        assert '!foo' not in out
        os.remove(self.test_yaml_file)

    def test_basic_process_seq_name_strip(self):
        yaml_docs = (
            ' - !bar\n'
            ' - blah\n'
        )

        with open(self.test_yaml_file, 'w') as out:
            out.write(yaml_docs)

        yp = val.YAMLProcessor(clean=False)
        out = yp.process(self.test_yaml_file)

        assert "bar:" in out
        os.remove(self.test_yaml_file)

    def test_empty_file_process(self):
        open(self.test_yaml_file, 'w').close()

        yp = val.YAMLProcessor(clean=False)
        nose.tools.assert_raises(
            util.YAMLError,
            yp.process, self.test_yaml_file
        )

        os.remove(self.test_yaml_file)

    def test_invalid_yaml_process(self):
        yaml_docs = """
        ---
        a: these newlines and white space break stuff
        ---
        b: processing wont even get here
        """
        open(self.test_yaml_file, 'w').close()

        yp = val.YAMLProcessor(clean=False)
        nose.tools.assert_raises(
            IOError,
            yp.process, '/tmp/thisFileDoesntExistAndWillCauseAnError'
        )

        os.remove(self.test_yaml_file)


class TestSchemaProcessor(object):
    def test_schema_load(self):
        """ Test variable settings from proper schema loading. """
        schemaproc = val.SchemaProcessor()

        # Test success
        schema = os.path.join(DATA_PATH, "testSchemaLoad1.json")
        schemaproc.load(schema)
        assert schemaproc.data is not None
        assert isinstance(schemaproc.data, dict)
        assert schemaproc.loaded
        assert schemaproc.schemafile == schemaproc._schemafile

    def test_schema_load_failure_bad_file(self):
        """ Test Exception raise on not existent file load. """
        schemaproc = val.SchemaProcessor()

        schema = os.path.join('not', 'a', 'valid', 'path.json')
        nose.tools.assert_raises(
            jsonschema.SchemaError,
            schemaproc.load, schema
        )

    def test_schema_load_failure_no_json_object(self):
        test_file_path = '/tmp/test.json'
        open(test_file_path, 'w').close()

        schemaproc = val.SchemaProcessor()

        nose.tools.assert_raises(
            jsonschema.SchemaError,
            schemaproc.load, test_file_path
        )

        os.remove(test_file_path)


class TestErrorHandler(object):
    def test_error_handler_init(self):
        eh = val.ErrorHandler('error', 'ymlfile', 'schemafile')
        assert eh.error == 'error'
        assert eh.ymlfile == 'ymlfile'
        assert eh.schemafile == 'schemafile'

    def test_process_bad_root_object(self):
        eh = val.ErrorHandler('error', 'ymlfile', 'schemafile')
        messages = []
        error = mock.MagicMock()
        error.message = "this is not of type u'object'"
        eh.process(1, [1, 2], error, messages)
        assert len(messages) == 1
        assert messages[0] == "Invalid root object in YAML. Check format."

    @mock.patch('ait.core.val.ErrorHandler.pretty')
    def test_process_docline_docnum_mismatch(self, pretty_mock):
        eh = val.ErrorHandler('error', 'ymlfile', 'schemafile')
        messages = []
        error = mock.MagicMock()
        error.message = "Some error message"
        eh.process(1, [1, 2, 3, 4], error, messages)
        assert pretty_mock.called
        pretty_mock.assert_called_with(3, 4, error, messages)

    @mock.patch('ait.core.val.ErrorHandler.pretty')
    def test_procces_with_single_doc(self, pretty_mock):
        eh = val.ErrorHandler('error', 'ymlfile', 'schemafile')
        messages = []
        error = mock.MagicMock()
        error.message = "Some error message"
        eh.process(1, [1, 2], error, messages)
        assert pretty_mock.called
        pretty_mock.assert_called_with(1, 3, error, messages)


def validate(args):
    msgs = []

    validator = val.Validator(*args)
    v = validator.validate(messages=msgs)
    # print validator
    return msgs, v


def dispmsgs(msgs):
    for msg in msgs:
        print "Validation Test Error: %s \n" % msg


def cmdval(args):
    msgs = []

    validator = val.CmdValidator(*args)
    v = validator.validate(messages=msgs)

    return msgs, v


def tlmval(args):
    msgs = []

    validator = val.TlmValidator(*args)
    v = validator.validate(messages=msgs)

    return msgs, v

def testYAMLProcesserLoad():
    ymlproc = val.YAMLProcessor()

    # Test bad path
    try:
        ymlfile = os.path.join('invalid', 'file', 'path.yaml')
        ymlproc.load(ymlfile)
        assert False
    except IOError:
        assert True
        assert not ymlproc.loaded

    # Test valid yaml
    ymlproc.load(os.path.join(DATA_PATH,  "testValidCmd1.yaml"))

    assert ymlproc.data is not None
    assert ymlproc.loaded


def testYAMLProcessorProcess():
    ymlproc = val.YAMLProcessor()
    ymlproc.process(os.path.join(DATA_PATH,  "testValidCmd1.yaml"))

    # check the document lines are correct
    doclines = [206]
    assert doclines == ymlproc.doclines

def testValidatorCmd():
    msgs = []

    # test successful validation
    msgs, v = validate([os.path.join(DATA_PATH,  "testValidCmd1.yaml"), cmd.getDefaultSchema()])
    assert v
    assert len(msgs) == 0

    # test failed validation
    msgs, v = validate([os.path.join(DATA_PATH,  "testInvalidCmd1.yaml"), cmd.getDefaultSchema()])

    assert not v
    assert len(msgs) == 1
    assert "Value 'BAD_OPCODE' should be of type 'integer'" in msgs[0]

def testCmdValidator():
    # test successful cmd validation
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testValidCmd1.yaml"), cmd.getDefaultSchema()])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0

    # test failed cmd validation - duplicate name
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator1.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Duplicate command name" in msgs[0]

    # test failed cmd validation - duplicate opcode
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator2.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Duplicate opcode" in msgs[0]

    # test failed cmd validation - bad argtype
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator3.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Invalid argument type" in msgs[0]

    # test failed cmd validation - bad nbytes
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator4.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 2
    assert "Invalid argument size" in msgs[0]

    # test failed cmd validation - bad byte order
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator5.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Invalid byte order" in msgs[0]

    # test failed cmd validation - bad start byte
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator6.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Invalid byte order" in msgs[0]

    # test success cmd validation - ensure quoted YAML booleans in enums
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator7.yaml"), cmd.getDefaultSchema()])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0

    # test failed cmd validation - YAML booleans not quoted
    msgs, v = cmdval([os.path.join(DATA_PATH,  "testCmdValidator8.yaml"), cmd.getDefaultSchema()])
    assert not v
    assert len(msgs) == 2
    assert "Invalid enum value" in msgs[0]

def testTlmValidator():
    # test successful tlm validation
    msgs, v = tlmval([os.path.join(DATA_PATH,  "testValidTlm1.yaml"), tlm.getDefaultSchema()])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0

    # test failed tlm validation - duplicate packet name
    try:
        msgs, v = tlmval([os.path.join(DATA_PATH,  "testTlmValidator1.yaml"), tlm.getDefaultSchema()])
        assert False
    except util.YAMLError, e:
        assert "Duplicate packet name" in e.message

    # test failed tlm validation - duplicate field name
    msgs, v = tlmval([os.path.join(DATA_PATH,  "testTlmValidator2.yaml"), tlm.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Duplicate field name" in msgs[0]

    # test failed tlm validation - invalid field type
    msgs, v = tlmval([os.path.join(DATA_PATH,  "testTlmValidator3.yaml"), tlm.getDefaultSchema()])
    assert not v
    assert len(msgs) == 1
    assert "Invalid field type" in msgs[0]

    # test failed tlm validation - invalid field size for field type specified
    msgs, v = tlmval([os.path.join(DATA_PATH,  "testTlmValidator4.yaml"), tlm.getDefaultSchema()])
    assert not v
    assert len(msgs) == 2
    assert "Invalid field size" in msgs[0]

    # test failed tlm validation - un-quoted YAML special variables in enumerations
    msgs, v = tlmval([os.path.join(DATA_PATH,  "testTlmValidator5.yaml"), tlm.getDefaultSchema()])
    assert not v
    assert len(msgs) == 2
    assert "Invalid enum value" in msgs[0]

    # test failed tlm validation - empty string for a YAML field
    msgs, v = tlmval([os.path.join(DATA_PATH,  "testTlmValidator6.yaml"), tlm.getDefaultSchema()])

    assert not v
    assert len(msgs) == 1
    assert "Missing value for desc." in msgs[0]


def testCmdDictValidation():
    # Validation test of current command dictionary
    msgs, v = cmdval([ait.config.cmddict.filename, cmd.getDefaultSchema()])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0


def testTlmDictValidation():
    # Validation test of current telemetry dictionary
    msgs, v = tlmval([ait.config.tlmdict.filename, tlm.getDefaultSchema()])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0


def testEvrValidation():
    # Validation test of current telemetry dictionary
    yml = ait.config.evrdict.filename
    schema = os.path.join(os.path.dirname(yml), evr.getDefaultSchema())
    msgs, v = validate([yml, schema])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0


def testTableValidation():
    # Validation test of current table configuration
    yml = ait.config.table.filename
    schema = pkg_resources.resource_filename('ait.core', 'data/table_schema.json')
    msgs, v = validate([yml, schema])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0

def testLimitsValidation():
    # Validation test of current table configuration
    yml = ait.config.limits.filename
    schema = pkg_resources.resource_filename('ait.core', 'data/limits_schema.json')
    msgs, v = validate([yml, schema])
    dispmsgs(msgs)
    assert v
    assert len(msgs) == 0


if __name__ == '__main__':
    nose.main()
