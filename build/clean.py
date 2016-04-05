#!/usr/bin/env python


import os
import pip

KEEP = 'pip setuptools wsgiref appdirs packaging pyparsing six'.split()

def system (cmd):
    print cmd
    os.system(cmd)

for pkg in [ pkg.key for pkg in pip.get_installed_distributions() ]:
    if pkg not in KEEP:
        system('pip uninstall -y %s' % pkg)

for name in '*~ *.pyc *.pkl'.split():
    system('find . -name "%s" -exec rm {} \;' % name)

system( 'python setup.py clean --all' )
system( 'rm -rf bliss_core.egg-info'  )
