Getting Started
===============

Before you install **bliss-core** you should install `virtualenv <https://virtualenv.pypa.io/en/latest/installation.html>`_ to properly isolate your development environment. It is also recommended that you install `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ for convenience. The following instructions will assume that you have installed both already.

Clone the repository from JPL Github:
$ git clone https://github.jpl.nasa.gov/bliss/bliss-core.git

First you need to make a virtual environment into which we'll install the bliss-core package and its dependencies:

.. code-block:: bash

    $ mkvirtualenv bliss-core-development

Install the bliss-core package and its dependencies in edit mode so you can continue to develop on the code.

.. code-block:: bash

    $ pip install -e .[docs,tests]

Note, if you don't want to be able to build the docs or run the unit tests you can save a small amount of dependency installation time by just running

.. code-block:: bash

    $ pip install -e .

Similarly, if you just want to install the additional documentation or test dependencies you can do so with the below commands:

.. code-block:: bash

    # Install the base dependencies and extra documentation dependencies
    $ pip install -e .[docs]

.. code-block:: bash

    # Install the base dependencies and extra unit test dependencies
    $ pip install -e .[tests]

BLISS uses two environment variables for configuration.

**BLISS_ROOT** is used for project wide pathing. If you don't set this BLISS will attempt to do a good job of it for you. If you want to be safe you should set it to the project root where you checked out the code.

**BLISS_CONFIG** is used for pointing BLISS at a configuration file. If you don't set this BLISS will fall back to **BLISS_ROOT** and try to locate a configuration file with that. If you're going to use the default test configuration that comes with bliss-core you should set this to:

.. code-block:: bash

    /<project root path>/data/config/config.yaml
