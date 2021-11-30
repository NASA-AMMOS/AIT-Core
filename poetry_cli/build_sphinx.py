import sys
from sphinx.cmd.build import main as build_main


def main():
    sys.exit(build_main([ 'doc/source', 'doc/build', '-a' ]))
