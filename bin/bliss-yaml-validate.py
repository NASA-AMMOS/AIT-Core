#!/usr/bin/env python
##
## usage: bliss-yaml-validate.py
##
## Validate YAML files with applicable schema and/or advanced
## content validation for CMD and TLM dictionaries.
##
## YAML validation is done through a combination of JSON Schema
## (http://json-schema.org/) and Python-coded content validation.
## The JSON Schema is used to validate general format of the YAML,
## i.e dictionaries contain the expected keys, values are the
## expected type, etc.
##
## Why JSON Schema? All of the available YAML validators did not
## meet the robustness expected for this tool. Since JSON and YAML
## are stored similarly in memory, the JSON Schema became an option.
## The only difference between YAML and JSON is the use of multiple
## documents in the same YAML file. The val.py module handles this
## implication. See TBD wiki page for more details on developing
## JSON schema for an applicable YAML file.
##
## Examples:
##
##   $ bliss-yaml-validate.py --cmd
##   $ bliss-yaml-validate.py --tlm
##   $ bliss-yaml-validate.py --evr
##   $ bliss-yaml-validate.py --cmd --yaml /path/to/cmd.yaml
##   $ bliss-yaml-validate.py --tlm --yaml /path/to/tlm.yaml
##   $ bliss-yaml-validate.py --yaml /path/to/yaml --schema /path/to/schema
##
## Authors: Jordan Padams
##


import sys
import os
import argparse

import bliss


def validate(validator, yml, schema):
    msgs = []
    validator = validator(yml, schema)
    valid = validator.validate(messages=msgs)

    msg = "Validation: %s: yml=%s, schema=%s"
    if valid:
        bliss.log.info(msg % ('SUCCESS', yml, schema))
    else:
        bliss.log.error(msg % ('FAILED', yml, schema))
        for msg in msgs:
            bliss.log.error(msg)


def main(options):
    bliss.log.begin()

    ymlarg = options.yaml
    schemaarg = options.schema
    cmd = options.cmd
    tlm = options.tlm
    evr = options.evr

    # Validate specified yaml file with specified schema
    if ymlarg is not None and schemaarg is not None:

        # Check yaml exists
        if not os.path.exists(ymlarg):
            raise os.error(ymlarg + " does not exist.")

        # Check schema exists
        if not os.path.exists(schemaarg):
            raise os.error(schemaarg + " does not exist.")

        validator = bliss.val.Validator
        validate(validator, ymlarg, schemaarg)

    else:

        if cmd:
            yml = bliss.cmd.getDefaultCmdDictFilename()
            schema = bliss.cmd.getDefaultSchema()
            validator = bliss.val.CmdValidator
        elif evr:
            yml = bliss.evr.getDefaultDictFilename()
            schema = bliss.evr.getDefaultSchema()
            validator = bliss.val.Validator
        elif tlm:
            yml = bliss.tlm.getDefaultDictFilename()
            schema = bliss.tlm.getDefaultSchema()
            validator = bliss.val.TlmValidator

        if ymlarg is not None:
            yml = ymlarg

        validate(validator, yml, schema)

    bliss.log.end()
    return 0


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="Validated a YAML configuration file "
                                        + "using the specified JSON schema file, as well as advanced "
                                        + "content validation for command and telemetry dictionaries.")

    argparser.add_argument('-y', '--yaml', metavar='</path/to/yaml>', type=str,
                           help='Path to YAML file.')
    argparser.add_argument('-s', '--schema', metavar='</path/to/schema>', type=str,
                           help='Path to JSON schema file.')
    argparser.add_argument('-c', '--cmd', action="store_true",
                           help='Command dictionary flag. If a YAML file is not ' +
                           'specified, the default command dictionary and ' +
                           'schema will be used.',
                           default=False)
    argparser.add_argument('-t', '--tlm', action="store_true",
                           help='Telemetry dictionary flag. If a YAML file is not ' +
                           'specified, the default telemetry dictionary and ' +
                           'schema will be used.',
                           default=False)
    argparser.add_argument('-e', '--evr', action="store_true",
                           help='EVR dictionary flag. If a YAML file is not ' +
                           'specified, the default command dictionary and ' +
                           'schema will be used.',
                           default=False)

    if len(sys.argv) < 2:
        argparser.print_help()
        sys.exit(1)
    else:
        options = argparser.parse_args()
        sys.exit(main(options))
