#!/usr/bin/env python
'''
usage: bliss_yaml_validate.py

Validate YAML files with applicable schema and/or advanced
content validation for CMD and TLM dictionaries.

YAML validation is done through a combination of JSON Schema
(http://json-schema.org/) and Python-coded content validation.
The JSON Schema is used to validate general format of the YAML,
i.e dictionaries contain the expected keys, values are the
expected type, etc.

Why JSON Schema? All of the available YAML validators did not
meet the robustness expected for this tool. Since JSON and YAML
are stored similarly in memory, the JSON Schema became an option.
The only difference between YAML and JSON is the use of multiple
documents in the same YAML file. The val.py module handles this
implication. See TBD wiki page for more details on developing
JSON schema for an applicable YAML file.

Examples:

  $ bliss-yaml-validate.py --cmd
  $ bliss-yaml-validate.py --tlm
  $ bliss-yaml-validate.py --evr
  $ bliss-yaml-validate.py --cmd --yaml /path/to/cmd.yaml
  $ bliss-yaml-validate.py --tlm --yaml /path/to/tlm.yaml
  $ bliss-yaml-validate.py --yaml /path/to/yaml --schema /path/to/schema
'''


import argparse
import os
import sys
import textwrap

from bliss.core import cmd, evr, log, tlm, val


def validate(validator, yml, schema):
    msgs      = []
    validator = validator(yml, schema)
    valid     = validator.validate(messages=msgs)

    msg = "Validation: %s: yml=%s, schema=%s"

    if valid:
        log.info(msg % ('SUCCESS', yml, schema))
        return 0
    else:
        log.error(msg % ('FAILED', yml, schema))
        for msg in msgs:
            log.error(msg)
        return 1


def main():
    argparser = argparse.ArgumentParser(
        description = """
Validate YAML files with applicable schema and/or advanced
content validation for CMD and TLM dictionaries.

YAML validation is done through a combination of JSON Schema
(http://json-schema.org/) and Python-coded content validation.  The
JSON Schema is used to validate general format of the YAML, i.e
dictionaries contain the expected keys, values are the expected type,
etc.

Why JSON Schema? All of the available YAML validators did not meet the
robustness expected for this tool. Since JSON and YAML are stored
similarly in memory, the JSON Schema became an option.  The only
difference between YAML and JSON is the use of multiple documents in
the same YAML file. The val.py module handles this implication. See
TBD wiki page for more details on developing JSON schema for an
applicable YAML file.
""",
        epilog = """
Examples:

    $ bliss-yaml-validate.py --cmd
    $ bliss-yaml-validate.py --tlm
    $ bliss-yaml-validate.py --evr
    $ bliss-yaml-validate.py --cmd --yaml /path/to/cmd.yaml
    $ bliss-yaml-validate.py --tlm --yaml /path/to/tlm.yaml
    $ bliss-yaml-validate.py --yaml /path/to/yaml --schema /path/to/schema
""",
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    argparser.add_argument(
        '-y', '--yaml',
        metavar = '</path/to/yaml>',
        type    = str,
        help    = 'Path to YAML file.'
    )

    argparser.add_argument(
        '-s', '--schema',
        metavar = '</path/to/schema>',
        type    = str,
        help    = 'Path to JSON schema file.'
    )

    argparser.add_argument(
        '-c', '--cmd',
        action  = 'store_true',
        default = False,
        help    = """Command dictionary flag. If a YAML file is not
        specified, the default command dictionary and schema will be used.
        """
    )

    argparser.add_argument(
        '-t', '--tlm',
        action  = 'store_true',
        default = False,
        help    = """Telemetry dictionary flag. If a YAML file is not
        specified, the default telemetry dictionary and schema will be used.
        """
    )

    argparser.add_argument(
        '-e', '--evr',
        action  = 'store_true',
        default = False,
        help    = """EVR dictionary flag. If a YAML file is not specified,
        the default command dictionary and schema will be used.
        """
    )

    if len(sys.argv) < 2:
        argparser.print_usage()
        print 'Run with --help for detailed help.'
        sys.exit(2)

    options = argparser.parse_args()

    log.begin()

    # Validate specified yaml file with specified schema
    if options.yaml is not None and options.schema is not None:
        # Check YAML exists
        if not os.path.exists(options.yaml):
            raise os.error(options.yaml + " does not exist.")

        # Check schema exists
        if not os.path.exists(options.schema):
            raise os.error(options.schema + " does not exist.")

        validator = val.Validator
        retcode = validate(validator, options.yaml, options.schema)

    else:
        if options.cmd:
            yml       = cmd.getDefaultDictFilename()
            schema    = cmd.getDefaultSchema()
            validator = val.CmdValidator
        elif options.evr:
            yml       = evr.getDefaultDictFilename()
            schema    = evr.getDefaultSchema()
            validator = val.Validator
        elif options.tlm:
            yml       = tlm.getDefaultDictFilename()
            schema    = tlm.getDefaultSchema()
            validator = val.TlmValidator

        if options.yaml is not None:
            yml = options.yaml

        retcode = validate(validator, yml, schema)

    log.end()
    return retcode


if __name__ == "__main__":
    main()
