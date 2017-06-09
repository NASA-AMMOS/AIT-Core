Installation and Environment Configuration
==========================================

The following guide will show you how to install and configure BLISS Core. For information on how to configure a new project to use BLISS, check out the `New Project Setup <project_setup>`_ page.

Installation
------------

Before you install **bliss-core** you should install `virtualenv <https://virtualenv.pypa.io/en/latest/installation.html>`_ to properly isolate your development environment. It is also recommended that you install `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ for convenience. The following instructions will assume that you have installed both already.

Clone the repository from JPL Github:

.. code-block:: bash

    $ git clone https://github.jpl.nasa.gov/bliss/bliss-core.git
    $ cd bliss-core

First you need to make a virtual environment into which we'll install the bliss-core package and its dependencies:

.. code-block:: bash

    $ mkvirtualenv bliss

Install the bliss-core package and its dependencies.

.. code-block:: bash

    $ pip install .

BLISS' Binary Stream Capture (BSC) module is used to capture data over Ethernet (Not supported on OS X), TCP, and
UDP connections. BSC supports the use of the `rawsocket <https://github.com/mwalle/rawsocket>`_
library so you can limit raw socket access on machines to specific users. `Rawsocket`
is not needed for BSC to function, however if you need this additional functionality
you will have to manually install the dependency with

.. code-block:: bash 

    $ pip install rawsocket

BLISS uses two environment variables for configuration.

**BLISS_ROOT** is used for project wide pathing. If you don't set this BLISS will attempt to do a good job of it for you. If you want to be safe you should set it to the project root where you checked out the code.  

**BLISS_CONFIG** environment variable for locating configuration information. This environment variable should contain a full path to a valid **config.yaml** file. If you don't set this BLISS will fail to initialize properly and will notify you that your configuration is invalid. If you wanted to set this to some example configuration that comes packaged with BLISS you could set this to:

.. code-block:: bash

    /<project root path>/test/config/config.yaml

We recommend that you set this in your **postactivate** file from **virtualenvwrapper**. This will ensure that each time you activate the virtual environment that your **BLISS_CONFIG** environment variable is set properly. By default, this file is located at **~/.virtualenvs/postactive**.

.. code-block:: bash

   if [ $VIRTUAL_ENV == "$HOME/.virtualenvs/bliss" ] 
   then
      export BLISS_ROOT=/path/to/bliss-core
      export BLISS_CONFIG=/path/to/bliss-core/data/config/config.yaml
   fi

Check Installation
------------------

Now that your installation has finished let's check that everything works as expected.

.. code-block:: bash

   # Deactivate your bliss virtual environment
   $ deactivate

   # Reactivate your bliss virtual environment to make sure we pick up the
   # new environment variable settings that you added
   $ workon bliss

   # Test that you can properly import the bliss.core package.
   $ python -c "import bliss.core"

If the last command **doesn't** generate any errors your installation is all set! If you see an error as shown below make sure to activate your virtual environment first.

.. code-block:: bash

   $ python -c "import bliss.core"
   Traceback (most recent call last):
     File "<string>", line 1, in <module>
   ImportError: No module named bliss.core

Working with BLISS
------------------

Your BLISS Core installation is now isolated to your virtual environment. Whenever you want to work on or run BLISS related code run **workon bliss** first to activate your environment. You will see a change in the format of your prompt indicating what environment you currently have active. If you want to disable the environment run **deactivate**.

.. code-block:: bash

   # Normal prompt
   $

   # Prompt after running workon
   (bliss)
   $
