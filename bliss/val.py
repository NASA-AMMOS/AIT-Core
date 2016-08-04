# Copyright 2015 California Institute of Technology.  ALL RIGHTS RESERVED.
# U.S. Government Sponsorship acknowledged.

"""
BLISS YAML Validator

The bliss.val module provides validation of content for YAML
files based on specified schema
"""

import os

import json
import yaml
from yaml.scanner import ScannerError
import re
import linecache
import jsonschema
import collections

import bliss


class YAMLProcessor (object):

    __slots__ = ["_ymlfile", "data", "loaded", "doclines", "_clean"]

    def __init__(self, ymlfile=None, clean=True):
        """Creates a new YAML validator for the given schema and yaml file

        The schema file should validate against JSON Schema Draft 4
        http://json-schema.org/latest/json-schema-core.html

        The YAML file should validate against the schema file given
        """
        self.loaded = False
        self.data = []
        self.doclines = []
        self._clean = clean

        self.ymlfile = ymlfile

    @property
    def ymlfile(self):
        return self._ymlfile

    @ymlfile.setter
    def ymlfile(self, yml):
        self._ymlfile = yml

        if yml is not None:
            self.load()

    def load(self, ymlfile=None):
        """Load and process the YAML file"""
        if ymlfile is not None:
            self._ymlfile = ymlfile

        try:
            # If yaml should be 'cleaned' of document references
            if self._clean:
                self.data = self.process(self.ymlfile)
            else:
                with open(self.ymlfile, 'rb') as stream:
                    for data in yaml.load_all(stream):
                        self.data.append(data)

            self.loaded = True
        except ScannerError, e:
            msg = "YAML formattting error - '" + self.ymlfile + ": '" + str(e) + "'"
            raise YAMLError(msg)

    def process(self, ymlfile):
        """Cleans out all document tags from the YAML file to make it
        JSON-friendly to work with the JSON Schema.
        """
        output = ""

        try:
            # Need a list of line numbers where the documents resides
            # Used for finding/displaying errors
            self.doclines = []
            linenum = None
            with open(ymlfile, 'r') as txt:
                for linenum, line in enumerate(txt):
                    # Pattern to match document start lines
                    doc_pattern = re.compile('(---) (![a-z]+)(.*$)', flags=re.I)

                    # Pattern to match sequence start lines
                    seq_pattern = re.compile('(\s*)(-+) !([a-z]+)(.*$)', flags=re.I)

                    # If we find a document, remove the tag
                    if doc_pattern.match(line):
                        line = doc_pattern.sub(r"---", line).lower()
                        self.doclines.append(linenum)
                    elif seq_pattern.match(line):
                        line = seq_pattern.sub(r"\1\2 \3: object", line).lower()

                    output = output + line

            if linenum is None:
                msg = "Empty YAML file: " + ymlfile
                raise YAMLError(msg)
            else:
                # Append one more document to docline for the end
                self.doclines.append(linenum+1)

            return output

        except IOError, e:
            msg = "Could not process YAML file '" + ymlfile + "': '" + str(e) + "'"
            raise IOError(msg)


class SchemaProcessor(object):

    __slots__ = ['_schemafile', 'data', '_proc_schema', 'loaded']

    def __init__(self, schemafile=None):
        """Creates a new YAML validator for the given schema and yaml file

        The schema file should validate against JSON Schema Draft 4
        http://json-schema.org/latest/json-schema-core.html

        The YAML file should validate against the schema file given
        """
        self.data = {}
        self.loaded = False

        self.schemafile = schemafile

    @property
    def schemafile(self):
        return self._schemafile

    @schemafile.setter
    def schemafile(self, schemafile):
        self._schemafile = schemafile

        if schemafile is not None:
            self.load()

    def load(self, schemafile=None):
        """Load and process the schema file"""
        if schemafile is not None:
            self._schemafile = schemafile

        try:
            self.data = json.load(open(self._schemafile))
        except (IOError, ValueError), e:
            msg = "Could not load schema file '" + self._schemafile + "': '" + str(e) + "'"
            raise jsonschema.SchemaError(msg)

        self.loaded = True


class ErrorHandler(object):

    __slots__ = ['error', 'doclines', 'ymlfile', 'schemafile', 'messages']

    def __init__(self, error=None, ymlfile=None, schemafile=None):
        self.error = error
        self.ymlfile = ymlfile
        self.schemafile = schemafile

    def process(self, docnum, doclines, error, messages=None):
        # TODO: Process the various types of errors
        start = doclines[docnum]+1
        if error.message.endswith("is not of type u'object'"):
            print error.message
            msg = "Invalid root object in YAML. Check format."
            messages.append(msg)
        elif len(doclines) > docnum+1:
            end = doclines[docnum+1]+1
            self.pretty(start, end, error, messages)
        else:
            # Only one value for doclines since only 1 doc
            self.pretty(1, start, error, messages)

    def pretty(self, start, end, error, messages=None):
        """Pretties up the output error message so it is readable
        and designates where the error came from"""

        bliss.log.debug("Displaying document from lines '%i' to '%i'", start, end)
        if len(error.relative_path) > 0:
            error_key = error.relative_path.pop()

            context = collections.deque(maxlen=20)
            tag = "        <<<<<<<<< Expects: %s <<<<<<<<<\n"""

            found = False
            for linenum in range(start, end):
                line = linecache.getline(self.ymlfile, linenum)

                # Check if line contains the error
                if ":" in line:
                    key, value = line.split(":")

                    # TODO:
                    # Handle maxItems TBD
                    # Handle minItems TBD
                    # Handle required TBD
                    # Handle in-order (bytes) TBD
                    # Handle uniqueness TBD

                    # Handle cases where key in yml file is hexadecimal
                    try:
                        key = int(key.strip(), 16)
                    except ValueError:
                        key = key.strip()

                    # Handle bad value data type
                    if error.validator == "type" and str(key) == error_key and \
                            value.strip() == str(error.instance):
                        errormsg = "Value should be of type '" + str(error.validator_value) + "'"

                        line = line.replace("\n", (tag % errormsg))
                        foundline = linenum
                        found = True

                # for the context queue, we want to get the error to appear in
                # the middle of the error output. to do so, we will only append
                # to the queue in 2 cases:
                #
                # 1. before we find the error (found == False). we can
                #    just keep pushing on the queue until we find it in the YAML.
                # 2. once we find the error (found == True), we just want to push
                #    onto the queue until the the line is in the middle
                if not found or (found and context.maxlen > (linenum-foundline)*2):
                    context.append(line)

            # Loop through the queue and generate a readable msg output
            out = ""
            for line in context:
                out += line

            msg = "Error found on line %d in %s:\n\n%s" % (foundline, self.ymlfile, out)
            messages.append(msg)

            linecache.clearcache()
        elif error.validator == "additionalProperties":
            if len(error.message) > 256:
                msg = error.message[:253] + "..."
            else:
                msg = error.message
            messages.append("Between lines %d - %d. %s" % (start, end, msg))
        else:
            messages.append(error.message)


class Validator(object):

    __slots__ = ['_ymlfile', '_schemafile', '_ymlproc', '_schemaproc', 'ehandler']

    def __init__(self, ymlfile, schemafile):
        """Creates a new YAML validator for the given schema and yaml file

        The schema file should validate against JSON Schema Draft 4
        http://json-schema.org/latest/json-schema-core.html

        The YAML file should validate against the schema file given
        """
        self._ymlfile = ymlfile
        self._schemafile = schemafile

        # Get the error handler ready, just in case
        self.ehandler = ErrorHandler(ymlfile=self._ymlfile, schemafile=self._schemafile)

    def validate(self, messages=None):
        """Provides schema_val validation for objects that do not override
        in domain-specific validator"""
        valid = self.schema_val(messages)
        return valid

    def schema_val(self, messages=None):
        "Perform validation with processed YAML and Schema"

        self._ymlproc = YAMLProcessor(self._ymlfile)
        self._schemaproc = SchemaProcessor(self._schemafile)

        valid = True

        bliss.log.debug("BEGIN: Schema-based validation for YAML '%s' with schema '%s'", self._ymlfile, self._schemafile)

        # Make sure the yml and schema have been loaded
        if self._ymlproc.loaded and self._schemaproc.loaded:
            # Load all of the yaml documents. Could be more than one in the same YAML file.
            for docnum, data in enumerate(yaml.load_all(self._ymlproc.data)):

                # Since YAML allows integer keys but JSON does not, we need to first
                # dump the data as a JSON string to encode all of the potential integers
                # as strings, and then read it back out into the YAML format. Kind of
                # a clunky workaround but it works as expected.
                data = yaml.load(json.dumps(data))

                # Now we want to get a validator ready
                v = jsonschema.Draft4Validator(self._schemaproc.data)

                # Loop through the errors (if any) and set valid = False if any are found
                for error in sorted(v.iter_errors(data)):
                    self.display_errors(docnum, error, messages)
                    valid = False

        elif not self._ymlproc.loaded:
            raise YAMLError("YAML must be loaded in order to validate.")
        elif not self._schemaproc.loaded:
            raise jsonschema.SchemaError("Schema must be loaded in order to validate.")

        bliss.log.debug("END: Schema-based validation complete for '%s'", self._ymlfile)
        return valid

    def display_errors(self, docnum, e, messages):
            # Display the error message
            if len(e.message) < 128:
                msg = "Schema-based validation failed for YAML file '" + self._ymlfile + "': '" + str(e.message) + "'"
            else:
                msg = "Schema-based validation failed for YAML file '" + self._ymlfile + "'"

            bliss.log.error(msg)
            self.ehandler.process(docnum, self._ymlproc.doclines, e, messages)


class CmdValidator (Validator):
    def __init__(self, ymlfile=None, schema=None):
        super(CmdValidator, self).__init__(ymlfile, schema)

    def validate(self, ymldata=None, messages=None):
        """Validates the Command Dictionary definitions"""

        schema_val = self.schema_val(messages)
        content_val = self.content_val(messages=messages)

        return schema_val and content_val

    def content_val(self, ymldata=None, messages=None):
        """Validates the Command Dictionary to ensure the contents for each of the fields
        meets specific criteria regarding the expected types, byte ranges, etc."""

        self._ymlproc = YAMLProcessor(self._ymlfile, False)

        # Turn off the YAML Processor
        bliss.log.debug("BEGIN: Content-based validation of Command dictionary")
        if ymldata is not None:
            cmddict = ymldata
        elif ymldata is None and self._ymlproc.loaded:
            cmddict = self._ymlproc.data
        elif not self._ymlproc.loaded:
            raise YAMLError("YAML failed to load.")

        try:
            # instantiate the document number. this will increment in order to
            # track the line numbers and section where validation fails
            docnum = 0

            # boolean to hold argument validity
            argsvalid = True

            # list of rules to validate against
            rules = []

            ### set the command rules
            #
            # set uniqueness rule for command names
            rules.append(UniquenessRule('name', "Duplicate command name: %s", messages))

            # set uniqueness rule for opcodes
            rules.append(UniquenessRule('opcode', "Duplicate opcode: %s", messages))
            #
            ###
            for cmdcnt, cmddefn in enumerate(cmddict[0]):
                # check the command rules
                for rule in rules:
                    rule.check(cmddefn)

                # list of argument rules to validate against
                argrules = []

                ### set rules for command arguments
                #
                # set uniqueness rule for opcodes
                argrules.append(UniquenessRule('name', "Duplicate argument name: " + cmddefn.name + ".%s", messages))

                # set type rule for arg.type
                argrules.append(TypeRule('type', "Invalid argument type for argument: " + cmddefn.name + ".%s", messages))

                # set argument size rule for arg.type.nbytes
                argrules.append(TypeSizeRule('nbytes', "Invalid argument size for argument: " + cmddefn.name + ".%s", messages))

                # set argument enumerations rule to check no enumerations contain un-quoted YAML special variables
                argrules.append(EnumRule('enum', "Invalid enum value for argument: " + cmddefn.name + ".%s", messages))

                # set byte order rule to ensure proper ordering of aruguments
                argrules.append(ByteOrderRule('bytes', "Invalid byte order for argument: " + cmddefn.name + ".%s", messages))
                #
                ###

                argdefns = cmddefn.argdefns
                for arg in argdefns:
                    # check argument rules
                    for rule in argrules:
                        rule.check(arg)

                # check if argument rule failed, if so set the validity to False
                if not all(r.valid is True for r in argrules):
                    argsvalid = False

            bliss.log.debug("END: Content-based validation complete for '%s'", self._ymlfile)

            # check validity of all command rules and argument validity
            return all(rule.valid is True for rule in rules) and argsvalid

        except bliss.val.YAMLValidationError, e:
            # Display the error message
            if messages is not None:
                if len(e.message) < 128:
                    msg = "Validation Failed for YAML file '" + self._yml + "': '" + str(e.message) + "'"
                else:
                    msg = "Validation Failed for YAML file '" + self._yml + "'"

                bliss.log.error(msg)
                self.ehandler.process(docnum, self.ehandler.doclines, e, messages)
                return False


class TlmValidator (Validator):
    def __init__(self, ymlfile=None, schema=None):
        super(TlmValidator, self).__init__(ymlfile, schema)

    def validate(self, ymldata=None, messages=None):
        """Validates the Telemetry Dictionary definitions"""

        schema_val = self.schema_val(messages)
        if len(messages) == 0:
            content_val = self.content_val(messages=messages)

        return schema_val and content_val

    def content_val(self, ymldata=None, messages=None):
        """Validates the Command Dictionary to ensure the contents for each of the fields
        meets specific criteria regarding the expected types, byte ranges, etc."""

        self._ymlproc = YAMLProcessor(self._ymlfile, False)

        # Turn off the YAML Processor
        bliss.log.debug("BEGIN: Content-based validation of Command dictionary")
        if ymldata is not None:
            tlmdict = ymldata
        elif ymldata is None and self._ymlproc.loaded:
            tlmdict = self._ymlproc.data
        elif not self._ymlproc.loaded:
            raise YAMLError("YAML failed to load.")

        try:
            # instantiate the document number. this will increment in order to
            # track the line numbers and section where validation fails
            docnum = 0

            # boolean to hold argument validity
            fldsvalid = True

            # list of rules to validate against
            rules = []

            ### set the command rules
            #
            # set uniqueness rule for command names
            rules.append(UniquenessRule('name', "Duplicate packet name: %s", messages))

            ###
            # Look through the telemetry dictionary
            # we access tlmdict[0] because the telemetry dictionary is a sequence
            # of packets in 1 document, so we know we can just begin by looping through
            # the first document of packets
            for pktcnt, pktdefn in enumerate(tlmdict[0]):
                # check the telemetry packet rules
                for rule in rules:
                    rule.check(pktdefn)

                # list of field rules to validate against
                fldrules = []

                ### set rules for telemetry fields
                #
                # set uniqueness rule for field name
                fldrules.append(UniquenessRule('name', "Duplicate field name: " + pktdefn.name + ".%s", messages))

                # set type rule for field.type
                fldrules.append(TypeRule('type', "Invalid field type for field: " + pktdefn.name + ".%s", messages))

                # set field size rule for field.type.nbytes
                fldrules.append(TypeSizeRule('nbytes', "Invalid field size for field: " + pktdefn.name + ".%s", messages))

                # set field enumerations rule to check no enumerations contain un-quoted YAML special variables
                fldrules.append(EnumRule('enum', "Invalid enum value for field: " + pktdefn.name + ".%s", messages))
                #
                ###

                flddefns = pktdefn.fields
                for fld in flddefns:
                    # check field rules
                    for rule in fldrules:
                        rule.check(fld)

                # check if field rule failed, if so set the validity to False
                if not all(r.valid is True for r in fldrules):
                    fldsvalid = False

            bliss.log.debug("END: Content-based validation complete for '%s'", self._ymlfile)

            # check validity of all packet rules and field validity
            return all(rule.valid is True for rule in rules) and fldsvalid

        except bliss.val.YAMLValidationError, e:
            # Display the error message
            if messages is not None:
                if len(e.message) < 128:
                    msg = "Validation Failed for YAML file '" + self._yml + "': '" + str(e.message) + "'"
                else:
                    msg = "Validation Failed for YAML file '" + self._yml + "'"

                bliss.log.error(msg)
                self.ehandler.process(self.ehandler.doclines, e, messages)
                return False


class ValidationRule(object):
    def __init__(self, attr, msg=None, messages=[]):
        self.attr = attr
        self.valid = True
        self.msg = msg
        self.messages = messages


class UniquenessRule(ValidationRule):
    """Checks the uniqueness of an attribute across YAML documents"""

    def __init__(self, attr, msg, messages=[]):
        """Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(UniquenessRule, self).__init__(attr, msg, messages)
        self.val_list = []

    def check(self, defn):
        """Performs the uniqueness check against the value list
        maintained in this rule objects
        """
        val = getattr(defn, self.attr)
        if val is not None and val in self.val_list:
            self.messages.append(self.msg % str(val))
            # TODO self.messages.append("TBD location message")
            self.valid = False
        elif val is not None:
            self.val_list.append(val)
            bliss.log.debug(self.val_list)


class TypeRule(ValidationRule):
    """Checks the object's type is an allowable types"""

    def __init__(self, attr, msg, messages=[]):
        """Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(TypeRule, self).__init__(attr, msg, messages)

    def check(self, defn):
        """Performs isinstance check for the definitions data type.

        Assumes the defn has 'type' and 'name' attributes
        """
        dtype = defn.type
        if not isinstance(dtype, bliss.dtype.PrimitiveType):
            self.messages.append(self.msg % str(defn.name))
            # self.messages.append("TBD location message")
            self.valid = False


class TypeSizeRule(ValidationRule):
    """Checks the object size matches the designated type"""

    def __init__(self, attr, msg, messages=[]):
        """Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(TypeSizeRule, self).__init__(attr, msg, messages)

    def check(self, defn, msg=None):
        """Uses the byte range in the object definition to determine
        the number of bytes and compares to the size defined in the type.

        Assumes the defn has 'type' and 'name' attributes, and a slice() method
        """
        dtype = defn.type
        if isinstance(dtype, bliss.dtype.PrimitiveType):
            # Check the nbytes designated in the YAML match the PDT
            nbytes = dtype.nbytes
            defnbytes = defn.slice().stop - defn.slice().start
            if nbytes != defnbytes:
                self.messages.append(self.msg % defn.name)
                self.messages.append("Definition size of (" + str(defnbytes) +
                                     " bytes) does not match size of data" +
                                     " type " +str(dtype.name) + " (" +
                                     str(nbytes) + " byte(s))")
                # TODO self.messages.append("TBD location message")
                self.valid = False


class EnumRule(ValidationRule):
    """Checks all enumerated values do not contain boolean keys.
    The YAML standard has a set of allowable boolean strings that are
    interpretted as boolean True/False unless explicitly quoted in the YAML
    file. The YAML boolean strings include (TRUE/FALSE/ON/OFF/YES/NO) .
    """
    def __init__(self, attr, msg, messages=[]):
        """Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(EnumRule, self).__init__(attr, msg, messages)

    def check(self, defn, msg=None):
        # Check enum does not contain boolean keys
        enum = defn.enum
        if enum is not None:
            for key in enum:
                val = enum.get(key)
                if type(key) is bool or type(val) is bool:
                    self.messages.append(self.msg % str(defn.name))
                    self.messages.append("Must enclose all YAML boolean " +
                                         "strings (TRUE/FALSE/ON/OFF/YES/NO) " +
                                         "with quotes.")
                    # TODO self.messages.append("TBD location message")
                    self.valid = False


class ByteOrderRule(ValidationRule):
    """Checks the byte ordering based on the previous set stop byte/bit"""

    def __init__(self, attr, msg, messages=[]):
        """Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(ByteOrderRule, self).__init__(attr, msg, messages)
        self.prevstop = 0

    def check(self, defn, msg=None):
        """Uses the definitions slice() method to determine its start/stop
        range.
        """
        # Check enum does not contain boolean keys
        if (defn.slice().start != self.prevstop):
            self.messages.append(self.msg % str(defn.name))
            # TODO self.messages.append("TBD location message")
            self.valid = False

        self.prevstop = defn.slice().stop


class YAMLValidationError(Exception):
    def __init__(self, arg):
        # Set some exception infomation
        self.msg = arg

        bliss.log.error(self.msg)


class YAMLError(Exception):
    def __init__(self, arg):
        # Set some exception infomation
        self.msg = arg

        bliss.log.error(self.msg)
