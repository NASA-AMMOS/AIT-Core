Bespoke Links to Instruments for Surface and Space (BLISS)
==========================================================

The Bespoke Links to Instruments for Surface and Space (BLISS) Ground Data
System (GDS) tools are a generalization of those developed for the
following JPL ISS projects:

  * [Vehicle Cabin Atmosphere Monitor (VCAM)](http://www.nasa.gov/mission_pages/station/research/experiments/35.html)

  * [Orbiting Carbon Observatory 3 (OCO-3)](http://oco.jpl.nasa.gov)

  * [ECOsystem Spaceborne Thermal Radiometer Experiment on Space Station (ECOSTRESS)](http://ecostress.jpl.nasa.gov)

Currently, the OCO-3 GDS tools are far ahead of the ECOSTRESS GDS
tools, but as the OCO-3 tools are generalized and made more
configurable, they'll be brought over to this repository.


Getting Started
---------------

You can read through the [Getting Started page](https://github.jpl.nasa.gov/pages/bliss/bliss-core/getting_started.html) for instruction on how to install BLISS Core.

You can read through the [new project getting started page](https://github.jpl.nasa.gov/pages/bliss/bliss-core/project_setup.html) for
instructions on how to use BLISS on your next project.


File and Directory Structure
----------------------------

    ├── bin          <--  Utilities and command line scripts
    ├── doc          <--  Project and API documentation
    ├── src/doc/dict <--  Cmd/Tlm Dictionary definitions and documentation
    ├── bliss        <--  BLISS Python source tree
    ├── data/config  <--  Example project configuration files


Developer Quickstart
====================

Before you install `bliss-core` you should install
[virtualenv](https://virtualenv.pypa.io/en/latest/installation.html) to properly
isolate your development environment. It is also recommended that you install
[virtualenvwrapper](https://virtualenvwrapper.readthedocs.org/en/latest/install.html)
for convenience. The following instructions will assume that you have installed
both already.

JPLers may clone (checkout) this repository from the [JPL
GitHub](https://github.jpl.nasa.gov):

    $ git clone https://github.jpl.nasa.gov/bliss/bliss-core.git

First you need to make a virtual environment into which we'll install the
`bliss-core` package and its dependencies:

    $ mkvirtualenv bliss-core-development

Install the `bliss-core` package and its dependencies in `edit` mode so you can
continue to develop on the code.

    $ pip install -e .[docs,tests]

Note, if you don't want to be able to build the docs or run the unit tests you
can save a small amount of dependency installation time by just running

    $ pip install -e .

Similarly, if you just want to install the additional documentation or test
dependencies you can do so with the below commands:

    # Install the base dependencies and extra documentation dependencies
    $ pip install -e .[docs]

    # Install the base dependencies and extra unit test dependencies
    $ pip install -e .[tests]

BLISS' BSC module is used to capture data over Ethernet (Not supported on OS X), TCP, and
UDP connections. BSC supports the use of the [rawsocket](https://github.com/mwalle/rawsocket)
library so you can limit raw socket access on machines to specific users. `Rawsocket`
is not needed for BSC to function, however if you need this additional functionality
you will have to manually install the dependency with

    $ pip install rawsocket

BLISS uses two environment variables for configuration.

`BLISS_ROOT` is used for project wide pathing. If you don't set this
BLISS will attempt to do a good job of it for you. If you want to be
safe you should set it to the project root where you checked out the code.

`BLISS_CONFIG` is used for pointing BLISS at a configuration file. If you don't
set this BLISS will fall back to `BLISS_ROOT` and try to locate a configuration
file with that. If you're going to use the default test configuration that
comes with `bliss-core` you should set this to:

    /<project root path>/data/config/config.yaml

Setting the above environment variables can be simplified by adding them to your
`virtualenvwrapper's postactivate` script. This file is sourced after you activate
a new environment with `workon`.

```
# Edit the postactivate script in your editor of choice. You can find it at $WORKON_HOME/postactivate

# Add the below to the file and update the paths to point to your checkout
if [ $VIRTUAL_ENV == "$WORKON_HOME/bliss-core-development" ]
then
    export BLISS_ROOT=/path/to/checkout/of/bliss-core
    export BLISS_CONFIG=$BLISS_ROOT/data/config/config.yaml
fi
```

Your BLISS Core configuration is now isolated to your `virtualenv` environment.
Whenever you want to work on BLISS run `workon bliss-core-development`. You
will see a change in the format of your prompt indicating what environment you
currently have active. If you want to disable the environment run `deactivate`.

```
# Normal prompt
>

# Prompt after running workon
(bliss-core-development)
>
```

You're now finished with installing BLISS Core. To quickly check that everything
went as expected run `python -c 'import bliss.core'` in a new terminal window.
You shouldn't see any message returned. If you receive an error as shown below
make sure you have activated your `virtualenv` environment first!

```
# Nominal
(bliss-core)
> python -c 'import bliss.core'
>

# Error!!!!
> python -c "import bliss.core"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ImportError: No module named bliss.core
>
```

Unit Tests
----------

BLISS uses the [Nose](https://nose.readthedocs.org/en/latest/) unit
test framework.  To run the tests in `python/bliss/test`:

    $ python setup.py nosetests


Documentation
-------------

BLISS uses Sphinx to build its documentation. You can build the documentation
with:

    $ python setup.py build_sphinx

To view the documentation, open `doc/build/html/index.html` in a web browser.

If you need to update the auto-generated documentation you can run the
following command to rebuild all of the `bliss` package documentation:

    $ sphinx-apidoc --separate --force --no-toc -o doc/source bliss bliss/test


Contributing
------------

To begin, clone the repository:

    $ git clone https://github.jpl.nasa.gov/bliss/bliss-core.git

After making a change to the code and ensuring all unit tests pass
(typing `make` will run all unit tests), ask Git for the current
"status" of your *local* repository:

    $ git status

The directions provided by `git status` should be self-explanatory.
To commit your changes, first "add" the files you changed to the Git
"index".  For example, suppose you edited this file, README.md:

    $ git add README.md

Run `git status` at any time to see the current status of the
repository, so after the addition:

    $ git status

Next commit changes that have been added to the Git index to your
*local* Git repository:

    $ git commit

Type a meaninful log message describing your changes.  By convention,
the first line of the log message summarizes the change(s) and is no
more than about 60 characters in length.  The next line is blank, and
subsequent lines provide a detailed description of the change(s), if
necessary.  Continuing the README.md example, the log message might
read:

    Updated README.md with Git instructions

    In this case a more detailed description probably isn't
    necessary, so this sentence is purely for illustrative
    purposes.

Finally, "push" your changes to the remote Git repository:

    $ git push

This will allow others to "pull" (receive) your changes into their
local repository:

    $ git pull

If others have pushed their changes since the last time you pulled,
you will need to pull first and then push your most recent changes:

    $ git pull
    $ git push


Authors
-------

BLISS authors (alphabetical):

  * Ben Bornstein
  * Erik Hovland
  * Michael Joyce
  * Alan Mazer
  * Jordan Padams
  * Alice Stanboli
