# Advanced Multi-Mission Operations System (AMMOS) Instrument Toolkit (AIT)
# Bespoke Link to Instruments and Small Satellites (BLISS)
#
# Copyright 2022, by the California Institute of Technology. ALL RIGHTS
# RESERVED. United States Government Sponsorship acknowledged. Any
# commercial use must be negotiated with the Office of Technology Transfer
# at the California Institute of Technology.
#
# This software may be subject to U.S. export control laws. By accepting
# this software, the user agrees to comply with all applicable U.S. export
# laws and regulations. User has the responsibility to obtain export licenses,
# or other export authority as may be required before exporting such
# information to foreign countries or providing access to foreign persons.

"""
AIT YAML Validator

The ait.core.val module provides validation of content for YAML
files based on specified schema.
"""

import json
import yaml
from yaml.scanner import ScannerError
import re
import linecache
import jsonschema
import collections

from ait.core import cmd, dtype, log, tlm, util


class YAMLProcessor(object):

    __slots__ = ["ymlfile", "data", "loaded", "doclines", "_clean"]

    def __init__(self, ymlfile=None, clean=True):
        """
        Creates a new YAML validator for the given schema and yaml file

        - The schema file should validate against JSON Schema Draft 4
        http://json-schema.org/latest/json-schema-core.html

        - The YAML file should validate against the schema file given
        """
        self.loaded = False
        self.data = []
        self.doclines = []
        self._clean = clean

        self.ymlfile = ymlfile

        if ymlfile is not None:
            self.load()

    def load(self, ymlfile=None):
        """Load and process the YAML file"""
        if ymlfile is not None:
            self.ymlfile = ymlfile

        try:
            # If yaml should be 'cleaned' of document references
            if self._clean:
                self.data = self.process(self.ymlfile)
            else:
                with open(self.ymlfile, "rb") as stream:
                    for data in yaml.load_all(stream, Loader=yaml.Loader):
                        self.data.append(data)
            self.loaded = True

        except ScannerError as e:
            msg = "YAML formatting error - '" + self.ymlfile + ": '" + str(e) + "'"
            raise util.YAMLError(msg)

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
            with open(ymlfile, "r") as txt:
                for linenum, line in enumerate(txt):
                    # Pattern to match document start lines
                    doc_pattern = re.compile(r"(---) (![a-z]+)(.*$)", flags=re.I)

                    # Pattern to match sequence start lines
                    seq_pattern = re.compile(r"(\s*)(-+) !([a-z]+)(.*$)", flags=re.I)

                    # If we find a document, remove the tag
                    if doc_pattern.match(line):
                        line = doc_pattern.sub(r"---", line).lower()
                        self.doclines.append(linenum)
                    elif seq_pattern.match(line):
                        # Replace the sequence start with key string
                        line = seq_pattern.sub(
                            r"\1\2 \3: line " + str(linenum), line
                        ).lower()

                    output = output + line

            if linenum is None:
                msg = "Empty YAML file: " + ymlfile
                raise util.YAMLError(msg)
            else:
                # Append one more document to docline for the end
                self.doclines.append(linenum + 1)

            return output

        except IOError as e:
            msg = "Could not process YAML file '" + ymlfile + "': '" + str(e) + "'"
            raise IOError(msg)


class SchemaProcessor(object):

    __slots__ = ["_schemafile", "data", "_proc_schema", "loaded"]

    def __init__(self, schemafile=None):
        """
        Creates a new YAML validator for the given schema and yaml file

        - The schema file should validate against JSON Schema Draft 4
        http://json-schema.org/latest/json-schema-core.html

        - The YAML file should validate against the schema file given
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
        except (IOError, ValueError) as e:
            msg = f"Could not load schema file {self._schemafile}: '{str(e)}'"
            raise jsonschema.SchemaError(msg)

        self.loaded = True


class ErrorHandler(object):
    """ErrorHandler class

    Leverages the jsonschema.exceptions.ValidationError API in order to extract
    useful information from the error to provide more detail on the root cause
    of the error.

    Refer to http://python-jsonschema.readthedocs.io/en/latest/errors/ for more
    information on JSON Schema errors.
    """

    __slots__ = ["error", "doclines", "ymlfile", "schemafile", "messages"]

    def __init__(self, error=None, ymlfile=None, schemafile=None):
        self.error = error
        self.ymlfile = ymlfile
        self.schemafile = schemafile

    def process(self, docnum, doclines, error, messages=None):
        # TODO: Process the various types of errors

        start = doclines[docnum] + 1
        if error.message.endswith("is not of type u'object'"):
            msg = "Invalid root object in YAML. Check format."
            messages.append(msg)
        elif len(doclines) > docnum + 1:
            end = doclines[docnum + 1] + 1
            self.pretty(start, end, error, messages)
        else:
            # Only one value for doclines since only 1 doc
            self.pretty(1, start, error, messages)

    def pretty(self, start, end, e, messages=None):
        """
        Pretties up the output error message, so it is readable
        and designates where the error came from
        """

        log.debug("Displaying document from lines '%i' to '%i'", start, end)

        errorlist = []
        if len(e.context) > 0:
            errorlist = e.context
        else:
            errorlist.append(e)

        for error in errorlist:
            validator = error.validator

            if validator == "required":
                # Handle required fields
                msg = error.message
                messages.append("Between lines %d - %d. %s" % (start, end, msg))
            elif validator == "additionalProperties":
                # Handle additional properties not allowed
                if len(error.message) > 256:
                    msg = error.message[:253] + "..."
                else:
                    msg = error.message
                    messages.append("Between lines %d - %d. %s" % (start, end, msg))
            elif len(error.relative_path) > 0:
                # Handle other cases where we can loop through the lines

                # get the JSON path to traverse through the file
                jsonpath = error.relative_path
                array_index = 0

                current_start = start
                foundline = 0
                found = False

                context = collections.deque(maxlen=20)
                tag = "        <<<<<<<<< Expects: %s <<<<<<<<<\n" ""
                for cnt, _path in enumerate(error.relative_path):

                    # Need to set the key we are looking, and then check the array count
                    # if it is an array, we have some interesting checks to do
                    if int(cnt) % 2 == 0:
                        # we know we have some array account
                        # array_index keeps track of the array count we are looking for or number
                        # of matches we need to skip over before we get to the one we care about

                        # check if previous array_index > 0. if so, then we know we need to use
                        # that one to track down the specific instance of this nested key.
                        # later on, we utilize this array_index loop through
                        # if array_index == 0:
                        array_index = jsonpath[cnt]

                        match_count = 0
                        continue
                    elif int(cnt) % 2 == 1:
                        # we know we have some key name
                        # current_key keeps track of the key we are looking for in the JSON Path
                        current_key = jsonpath[cnt]

                    for linenum in range(current_start, end):
                        line = linecache.getline(self.ymlfile, linenum)

                        # Check if line contains the error
                        if ":" in line:
                            l_split = line.split(":")
                            key = l_split[0]
                            value = ":".join(l_split[1:])

                            # TODO:
                            # Handle maxItems TBD
                            # Handle minItems TBD
                            # Handle in-order (bytes) TBD
                            # Handle uniqueness TBD

                            # Handle cases where key in yml file is hexadecimal
                            try:
                                key = int(key.strip(), 16)
                            except ValueError:
                                key = key.strip()

                            if str(key) == current_key:
                                # check if we are at our match_count and end of the path
                                if match_count == array_index:
                                    # check if we are at end of the jsonpath
                                    if cnt == len(jsonpath) - 1:
                                        # we are at the end of path so let's stop here'
                                        if error.validator == "type":
                                            if value.strip() == str(error.instance):
                                                errormsg = (
                                                    "Value '%s' should be of type '%s'"
                                                    % (
                                                        error.instance,
                                                        str(error.validator_value),
                                                    )
                                                )
                                                line = line.replace(
                                                    "\n", (tag % errormsg)
                                                )
                                                foundline = linenum
                                                found = True
                                            elif (
                                                value.strip() == ""
                                                and error.instance is None
                                            ):
                                                errormsg = "Missing value for %s." % key
                                                line = line.replace(
                                                    "\n", (tag % errormsg)
                                                )
                                                foundline = linenum
                                                found = True

                                    elif not found:
                                        # print "EXTRA FOO"
                                        # print match_count
                                        # print array_index
                                        # print current_key
                                        # print line
                                        # otherwise change the start to the current line
                                        current_start = linenum
                                        break

                                match_count += 1

                        # for the context queue, we want to get the error to appear in
                        # the middle of the error output. to do so, we will only append
                        # to the queue in 2 cases:
                        #
                        # 1. before we find the error (found == False). we can
                        #    just keep pushing on the queue until we find it in the YAML.
                        # 2. once we find the error (found == True), we just want to push
                        #    onto the queue until the the line is in the middle
                        if not found or (
                            found and context.maxlen > (linenum - foundline) * 2
                        ):
                            context.append(line)
                        elif found and context.maxlen <= (linenum - foundline) * 2:
                            break

                    # Loop through the queue and generate a readable msg output
                    out = ""
                    for line in context:
                        out += line

                    if foundline:
                        msg = "Error found on line %d in %s:\n\n%s" % (
                            foundline,
                            self.ymlfile,
                            out,
                        )
                        messages.append(msg)

                        # reset the line it was found on and the context
                        foundline = 0
                        context.clear()

                    linecache.clearcache()
            else:
                messages.append(error.message)


class Validator(object):

    __slots__ = ["_ymlfile", "_schemafile", "_ymlproc", "_schemaproc", "ehandler",
                 "validate_list", "yml_dir", "yml_files_to_validate"]

    def __init__(self, ymlfile, schemafile):
        """
        Creates a new YAML validator for the given schema and yaml file

        - The schema file should validate against JSON Schema Draft 4
        http://json-schema.org/latest/json-schema-core.html

        - The YAML file should validate against the schema file given
        """
        self._ymlfile = ymlfile
        self._schemafile = schemafile
        self._ymlproc = None
        # Get the error handler ready, just in case
        self.ehandler = ErrorHandler(ymlfile=self._ymlfile, schemafile=self._schemafile)
        # Declare variables used for validating nested yaml files
        self.validate_list = []
        self.yml_dir = f"{ymlfile.rsplit('/', 1)[0]}/"
        self.yml_files_to_validate = self.get_included_files(ymlfile)

    def get_included_files(self, yml_file):
        """
        Make a list of  yaml files to validate against the schema.  The first member
        of the list will include the full path to the yaml file.
        The next element will the module yml file (e.g. cmd.yml),
        followed by the names of any included files.
        The assumption is made that all the included yml files are
        found in the same directory as the module yml file.

        Parameters
        ----------
        yml_file : str
            The module yaml file to validate (cmd.yml or tlm.yml)

        Returns
        -------
        self.validate_list: list
            A set of all files that are to be validated.

        """
        # The first yaml file to validate will include a full path
        # Any included yaml files will have the path added.
        if '/' in yml_file:
            self.validate_list.append(yml_file)
        else:
            yml_file = f'{self.yml_dir}/{yml_file}'

        try:
            with open(yml_file, "r") as yml_fh:
                for line in yml_fh:
                    if not line.strip().startswith("#") and "!include" in line:
                        included_file_name = line.split('!include ')[-1].strip()
                        self.validate_list.append(f'{self.yml_dir}/{included_file_name}')
                        # Look for includes within included file
                        self.get_included_files(included_file_name)
                # Check and flag multiple includes
                if len(self.validate_list) != len(set(self.validate_list)):
                    log.info(f'WARNING: Validate: Duplicate config files in the '
                             f'include tree. {self.validate_list}')
                return set(self.validate_list)
        except RecursionError as e:
            log.info(
                f'ERROR: {e}: Infinite loop: check that yaml config files are not looping '
                'back and forth on one another through the "!include" statements.'
            )

    def validate_schema(self, messages=None):
        """
        Provides schema_val validation for objects that do not override
        in domain-specific validator (evr.yaml, table.yaml, limits.yaml)

        Returns
        -------
        valid boolean:
            The result of the schema test (True(Pass)/False(Fail))
        """
        valid = self.schema_val(messages)
        return valid

    def validate(self, ymldata=None, messages=None):
        """
        Validates the Command or Telemetry Dictionary definitions
        The method will validate module (cmd.yml or tlm.yaml) and included yaml config files

        Returns
        -------
        schema_val boolean:
            The result of the schema test (True/False)

        content_val boolean:
            Results of the schema test on config and included files
                True - all the tested yaml files passed the schema test
                False - one or more yaml files did not pass the schema test

        """
        content_val_list = []
        schema_val = self.schema_val(messages)

        # Loop through the list of all the tested yaml files
        for yaml_file in self.yml_files_to_validate:
            log.info(f"Validating: {yaml_file}")
            content_val_list.append(self.content_val(yaml_file, messages=messages))

        if all(content_val_list):  # Test that all tested files returned True
            content_val = True
        else:
            content_val = False

        return schema_val and content_val

    def schema_val(self, messages=None):
        """Perform validation with processed YAML and Schema"""
        self._ymlproc = YAMLProcessor(self._ymlfile)
        self._schemaproc = SchemaProcessor(self._schemafile)
        valid = True

        log.debug(
            "BEGIN: Schema-based validation for YAML '%s' with schema '%s'",
            self._ymlfile,
            self._schemafile,
        )

        # Make sure the yml and schema have been loaded
        if self._ymlproc.loaded and self._schemaproc.loaded:
            # Load all of the yaml documents. Could be more than one in the same YAML file.
            for docnum, data in enumerate(
                yaml.load_all(self._ymlproc.data, Loader=yaml.Loader)
            ):
                # Since YAML allows integer keys but JSON does not, we need to first
                # dump the data as a JSON string to encode all of the potential integers
                # as strings, and then read it back out into the YAML format. Kind of
                # a clunky workaround but it works as expected.
                data = yaml.load(json.dumps(data), Loader=yaml.Loader)

                # Now we want to get a validator ready
                v = jsonschema.Draft4Validator(self._schemaproc.data)

                # Loop through the errors (if any) and set valid = False if any are found
                # Display the error message
                for error in v.iter_errors(data):
                    msg = (
                        f"Schema-based validation failed for YAML file ' {self._ymlfile} '"
                    )
                    self.ehandler.process(
                        docnum, self._ymlproc.doclines, error, messages
                    )
                    valid = False

                if not valid:
                    log.error(msg)

        elif not self._ymlproc.loaded:
            raise util.YAMLError("YAML must be loaded in order to validate.")
        elif not self._schemaproc.loaded:
            raise jsonschema.SchemaError("Schema must be loaded in order to validate.")

        log.debug("END: Schema-based validation complete for '%s'", self._ymlfile)
        return valid

    def content_val(self, yaml_file, ymldata=None, messages=None):
        """Simple base content_val method - needed for unit tests"""
        self._ymlproc = YAMLProcessor(yaml_file, False)


class CmdValidator(Validator):
    def __init__(self, ymlfile=None, schema=None):
        super(CmdValidator, self).__init__(ymlfile, schema)

    def content_val(self, yaml_file, ymldata=None, messages=None):
        """
        Validates the Command Dictionary to ensure the contents for each of the fields
        meets specific criteria regarding the expected types, byte ranges, etc.
        """

        self._ymlproc = YAMLProcessor(yaml_file, False)

        # Turn off the YAML Processor
        log.debug("BEGIN: Content-based validation of Command dictionary")
        if ymldata is not None:
            cmddict = ymldata
        else:
            cmddict = cmd.CmdDict(self._ymlfile)
        try:
            # instantiate the document number. this will increment in order to
            # track the line numbers and section where validation fails
            docnum = 0

            # boolean to hold argument validity
            argsvalid = True

            # list of rules to validate against
            rules = []

            # set the command rules
            # set uniqueness rule for command names
            rules.append(UniquenessRule("name", "Duplicate command name: %s", messages))

            # set uniqueness rule for opcodes
            rules.append(UniquenessRule("opcode", "Duplicate opcode: %s", messages))

            for key in cmddict.keys():
                cmddefn = cmddict[key]
                for rule in rules:
                    rule.check(cmddefn)

                # list of argument rules to validate against
                argrules = []

                # set rules for command arguments
                # set uniqueness rule for opcodes
                argrules.append(
                    UniquenessRule(
                        "name",
                        "Duplicate argument name: " + cmddefn.name + ".%s",
                        messages,
                    )
                )

                # set type rule for arg.type
                argrules.append(
                    TypeRule(
                        "type",
                        "Invalid argument type for argument: " + cmddefn.name + ".%s",
                        messages,
                    )
                )

                # set argument size rule for arg.type.nbytes
                argrules.append(
                    TypeSizeRule(
                        "nbytes",
                        "Invalid argument size for argument: " + cmddefn.name + ".%s",
                        messages,
                    )
                )

                # set argument enumerations rule to check no enumerations contain un-quoted YAML special variables
                argrules.append(
                    EnumRule(
                        "enum",
                        "Invalid enum value for argument: " + cmddefn.name + ".%s",
                        messages,
                    )
                )

                # set byte order rule to ensure proper ordering of aruguments
                argrules.append(
                    ByteOrderRule(
                        "bytes",
                        "Invalid byte order for argument: " + cmddefn.name + ".%s",
                        messages,
                    )
                )
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

            log.debug("END: Content-based validation complete for '%s'", self._ymlfile)

            # check validity of all command rules and argument validity
            return all(rule.valid is True for rule in rules) and argsvalid

        except util.YAMLValidationError as e:
            # Display the error message
            if messages is not None:
                if len(e.message) < 128:
                    msg = (
                        "Validation Failed for YAML file '"
                        + self._ymlfile
                        + "': '"
                        + str(e.message)
                        + "'"
                    )
                else:
                    msg = "Validation Failed for YAML file '" + self._ymlfile + "'"

                log.error(msg)
                self.ehandler.process(docnum, self.ehandler.doclines, e, messages)
                return False


class TlmValidator(Validator):
    def __init__(self, ymlfile=None, schema=None):
        super(TlmValidator, self).__init__(ymlfile, schema)

    def content_val(self, yaml_file, ymldata=None, messages=None):
        """
        Validates the Telemetry Dictionary to ensure the contents for each of the fields
        meets specific criteria regarding the expected types, byte ranges, etc.
        """

        self._ymlproc = YAMLProcessor(yaml_file, False)

        # Turn off the YAML Processor
        log.debug("BEGIN: Content-based validation of Telemetry dictionary")
        if ymldata is not None:
            tlmdict = ymldata
        else:
            tlmdict = tlm.TlmDict(self._ymlfile)

        try:
            # boolean to hold argument validity
            fldsvalid = True

            # list of rules to validate against
            rules = []

            # set the packet rules
            # set uniqueness rule for packet names
            rules.append(UniquenessRule("name", "Duplicate packet name: %s", messages))

            # Loop through the keys and check each PacketDefinition
            for key in tlmdict.keys():
                pktdefn = tlmdict[key]
                # check the telemetry packet rules
                for rule in rules:
                    rule.check(pktdefn)

                # list of field rules to validate against
                fldrules = []

                # set rules for telemetry fields
                # set uniqueness rule for field name
                fldrules.append(
                    UniquenessRule(
                        "name",
                        "Duplicate field name: " + pktdefn.name + ".%s",
                        messages,
                    )
                )

                # set type rule for field.type
                fldrules.append(
                    TypeRule(
                        "type",
                        "Invalid field type for field: " + pktdefn.name + ".%s",
                        messages,
                    )
                )

                # set field size rule for field.type.nbytes
                fldrules.append(
                    TypeSizeRule(
                        "nbytes",
                        "Invalid field size for field: " + pktdefn.name + ".%s",
                        messages,
                    )
                )

                # set field enumerations rule to check no enumerations contain un-quoted YAML special variables
                fldrules.append(
                    EnumRule(
                        "enum",
                        "Invalid enum value for field: " + pktdefn.name + ".%s",
                        messages,
                    )
                )
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

            log.debug("END: Content-based validation complete for '%s'", self._ymlfile)

            # check validity of all packet rules and field validity
            return all(rule.valid is True for rule in rules) and fldsvalid

        except util.YAMLValidationError as e:
            # Display the error message
            if messages is not None:
                if len(e.message) < 128:
                    msg = (
                        "Validation Failed for YAML file '"
                        + self._ymlfile
                        + "': '"
                        + str(e.message)
                        + "'"
                    )
                else:
                    msg = "Validation Failed for YAML file '" + self._ymlfile + "'"

                log.error(msg)
                self.ehandler.process(self.ehandler.doclines, e, messages)
                return False


class ValidationRule(object):
    def __init__(self, attr, msg=None, messages=[]):  # noqa
        self.attr = attr
        self.valid = True
        self.msg = msg
        self.messages = messages


class UniquenessRule(ValidationRule):
    """Checks the uniqueness of an attribute across YAML documents"""

    def __init__(self, attr, msg, messages=[]):  # noqa
        """
        Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(UniquenessRule, self).__init__(attr, msg, messages)
        self.val_list = []

    def check(self, defn):
        """
        Performs the uniqueness check against the value list
        maintained in this rule objects

        Parameters
        __________
        defn : class
           Class containing attributes to check.
              - e.g CmdDefn, ArgDef

        """

        val = getattr(defn, self.attr)

        if val is not None and val in self.val_list:
            self.messages.append(self.msg % str(val))
            # TODO self.messages.append("TBD location message")
            self.valid = False
        elif val is not None:
            self.val_list.append(val)


class TypeRule(ValidationRule):
    """Checks the object's type is an allowable types"""

    def __init__(self, attr, msg, messages=[]):  # noqa
        """
        Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(TypeRule, self).__init__(attr, msg, messages)

    def check(self, defn):
        """
        Performs isinstance check for the definitions' data type.
        Assumes the defn has 'type' and 'name' attributes
        """
        allowed_types = dtype.PrimitiveType, dtype.ArrayType
        if not isinstance(defn.type, allowed_types):
            self.messages.append(self.msg % str(defn.name))
            # self.messages.append("TBD location message")
            self.valid = False


class TypeSizeRule(ValidationRule):
    """Checks the object size matches the designated type"""

    def __init__(self, attr, msg, messages=[]):  # noqa
        """
        Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(TypeSizeRule, self).__init__(attr, msg, messages)

    def check(self, defn, msg=None):
        """Uses the byte range in the object definition to determine
        the number of bytes and compares to the size defined in the type.

        Assumes the defn has 'type' and 'name' attributes, and a slice() method
        """
        if isinstance(defn.type, dtype.PrimitiveType):
            # Check the nbytes designated in the YAML match the PDT
            nbytes = defn.type.nbytes
            defnbytes = defn.slice().stop - defn.slice().start
            if nbytes != defnbytes:
                self.messages.append(self.msg % defn.name)
                self.messages.append(
                    "Definition size of ("
                    + str(defnbytes)
                    + " bytes) does not match size of data"
                    + " type "
                    + str(defn.type.name)
                    + " ("
                    + str(nbytes)
                    + " byte(s))"
                )
                # TODO self.messages.append("TBD location message")
                self.valid = False


class EnumRule(ValidationRule):
    """
    Checks all enumerated values do not contain boolean keys.
    The YAML standard has a set of allowable boolean strings that are
    interpreted as boolean True/False unless explicitly quoted in the YAML
    file. The YAML boolean strings include (TRUE/FALSE/ON/OFF/YES/NO) .
    """

    def __init__(self, attr, msg, messages=[]):  # noqa
        """
        Takes in an attribute name, error message, and list of error
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
                    self.messages.append(
                        "Must enclose all YAML boolean "
                        + "strings (TRUE/FALSE/ON/OFF/YES/NO) "
                        + "with quotes."
                    )
                    # TODO self.messages.append("TBD location message")
                    self.valid = False


class ByteOrderRule(ValidationRule):
    """Checks the byte ordering based on the previous set stop byte/bit"""

    def __init__(self, attr, msg, messages=[]):  # noqa
        """
        Takes in an attribute name, error message, and list of error
        messages to append to
        """
        super(ByteOrderRule, self).__init__(attr, msg, messages)
        self.prevstop = 0

    def check(self, defn, msg=None):
        """
        Uses the definitions slice() method to determine its start/stop
        range.
        """
        # Check enum does not contain boolean keys
        if defn.slice().start != self.prevstop:
            self.messages.append(self.msg % str(defn.name))
            # TODO self.messages.append("TBD location message")
            self.valid = False

        self.prevstop = defn.slice().stop
