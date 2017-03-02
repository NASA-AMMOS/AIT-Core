#!/usr/bin/env python


import os
import re
import sys


isdir  = os.path.isdir
isfile = os.path.isfile
join   = os.path.join


def endswith (s, suffixes):
    if type(suffixes) is str:
        suffixes = [ suffixes ]

    for suffix in suffixes:
        if s.endswith(suffix):
            return True

    return False


def index (dirname, names):
    with open( join(dirname, 'index.html'), 'w' ) as output:
        output.write('<!doctype html>\n')
        output.write('<body>\n')

        for name in names:
            output.write('  <a href="%s">%s</a><br>\n' % (name, name))

        output.write('</body>\n')


def ispkg (filename):
    extensions = '.tar.gz', '.whl', '.zip'
    return isfile(filename) and endswith(filename, extensions)
        

def normalize (name):
    return re.sub(r'[-_.]+', '-', name).lower()


def organize (dirname):
    for name in os.listdir(dirname):
        pathname = join(dirname, name)
        if ispkg(pathname):
            pkgpath = join(dirname, pkgname(name))
            system('mkdir -p %s' % pkgpath)
            system('mv %s %s'    % (pathname, pkgpath))


def pkgname (name):
    parts = [ ]

    for part in name.split('-'):
        if part[0].isdigit():
            break
        else:
            parts.append(part)

    return normalize( '-'.join(parts) )


def system (cmd):
    print cmd
    os.system(cmd)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print '  usage: simple.py directory'
        print
        print '  Creates a PEP 503 -- Simple Repository API compliant PyPI'
        print '  repository in the given directory containing Python packages'
        print '  downloaded with "pip download".  For example:'
        print
        print '      $ mkdir simple'
        print '      $ pip download -d simple -r requirements.txt'
        print '      $ ./simply.py simple'
        print
        sys.exit(2)

    root   = sys.argv[1]
    organize(root)

    packages = [ s for s in os.listdir(root) if isdir( join(root, s) ) ]
    packages.sort()
    index(root, packages)

    for pkg in packages:
        path  = join(root, pkg)
        files = [ s for s in os.listdir(path) if ispkg( join(path, s)) ]
        files.sort()
        index(path, files)

    print 'Done.  Indexed %d packages in "%s".' % (len(packages), root)
