Installation and Environment Configuration
==========================================

The following guide will show you how to install and configure BLISS Core. For information on how to configure a new project to use BLISS, check out the `New Project Setup <project_setup>`_ page.

Installation
------------

Before you install BLISS Core you should install `virtualenv <https://virtualenv.pypa.io/en/latest/installation.html>`_ to properly isolate your development environment. It is also recommended that you install `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ for convenience. The following instructions will assume that you have installed both already and created an environment.

You can install BLISS Core from a checkout of the code or from the BLISS PyPi server. Having a checkout of the code can be handy if you want to view the source or make changes. Installing from PyPi keeps your system clutter free since you don’t have a copy of the code base around. Either choice will work fine!

From Code Checkout
^^^^^^^^^^^^^^^^^^

Clone the repository from JPL Github:

.. code-block:: bash

    $ git clone https://github.jpl.nasa.gov/bliss/bliss-core.git
    $ cd bliss-core

Find the latest tagged version of the code and check it out:

.. code-block:: bash

   $ git tag
   $ git checkout <Most recent version number output by the previous command>


Install the **bliss.core** package and its dependencies:

.. code-block:: bash

    $ pip install .

From BLISS PyPi
^^^^^^^^^^^^^^^

If you have access to the JPL network you can install BLISS Core directly from the BLISS PyPi server.

.. code-block:: bash

    $ pip install bliss-core --extra-index-url https://bliss.jpl.nasa.gov/pypi/simple/


Optional Binary Stream Capture Components
-----------------------------------------

BLISS' Binary Stream Capture (BSC) module is used to capture data over Ethernet (Not supported on OS X), TCP, and
UDP connections. BSC supports the use of the `rawsocket <https://github.com/mwalle/rawsocket>`_
library so you can limit raw socket access on machines to specific users. **Rawsocket**
is not needed for BSC to function, however if you need this additional functionality
you will have to manually install the dependency with:

.. code-block:: bash 

    $ pip install rawsocket

Environment Configuration
-------------------------

BLISS uses two environment variables for configuration.

**BLISS_ROOT** is used for project wide pathing. If you don't set this BLISS will attempt to do a good job of it for you. If you want to be safe you should set it to the project root where you checked out the code.  

**BLISS_CONFIG** is used for locating the project's YAML configuration file. This environment variable should contain a full path to a valid **config.yaml** file. If you don't set this BLISS will fail to initialize properly and will notify you that your configuration is invalid. If you wanted to set this to some example configuration that comes packaged with BLISS you could set this to:

.. code-block:: bash

    /<project root path>/data/config/config.yaml

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

Your BLISS Core installation is now isolated to your virtual environment. Whenever you want to work on or run BLISS related code run ``workon bliss`` first to activate your environment. You will see a change in the format of your prompt indicating what environment you currently have active. If you want to disable the environment run ``deactivate``.

.. code-block:: bash

   # Normal prompt
   $

   # Prompt after running workon
   (bliss)
   $

Upgrading an Installation
-------------------------

When a new version of BLISS Core is released you'll most likely want to upgrade your environment. You'll need to upgrade differently depending on how you installed the system.

Installed from Code Checkout
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Navigate back to the directory where you checked out the code and run the following commands to pull the latest code, checkout the latest tag, and upgrade your install.

.. code-block:: bash

   $ git checkout master
   $ git pull
   $ git tag
   $ git checkout <Most recent version number output by the previous command>
   $ pip install . --upgrade

Installed from PyPi
^^^^^^^^^^^^^^^^^^^

Run the following to upgrade to the latest BLISS Core versions.

.. code-block:: bash

   $ pip install bliss-core --extra-index-url https://bliss.jpl.nasa.gov/pypi/simple/ --upgrade
