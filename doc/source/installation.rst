Installation and Environment Configuration
==========================================

The following guide will show you how to install and configure AIT Core. For information on how to configure a new project to use AIT, check out the `New Project Setup <project_setup.html>`_ page.

Installation
------------

Before you install AIT Core you should install `virtualenv <https://virtualenv.pypa.io/en/latest/installation.html>`_ to properly isolate your development environment. It is also recommended that you install `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ for convenience. The following instructions will assume that you have installed both already and created an environment.

You can install AIT Core from a checkout of the code or from the AIT PyPi server. Having a checkout of the code can be handy if you want to view the source or make changes. Installing from PyPi keeps your system clutter free since you don’t have a copy of the code base around. Either choice will work fine!

From Code Checkout
^^^^^^^^^^^^^^^^^^

Clone the repository from Github:

.. code-block:: bash

    $ git clone https://github.com/NASA-AMMOS/AIT-Core.git
    $ cd AIT-Core

Find the latest tagged version of the code and check it out:

.. code-block:: bash

   $ git tag
   $ git checkout <Most recent version number output by the previous command>


Install the **ait.core** package and its dependencies:

.. code-block:: bash

    $ pip install .

From PyPi
^^^^^^^^^^^^^^^

You can also install AIT Core directly from PyPi if you don't want to keep a local copy of the code.

.. code-block:: bash

    $ pip install ait-core


Optional Binary Stream Capture Components
-----------------------------------------

AIT's Binary Stream Capture (BSC) module is used to capture data over Ethernet (Not supported on OS X), TCP, and
UDP connections. BSC supports the use of the `rawsocket <https://github.com/mwalle/rawsocket>`_
library so you can limit raw socket access on machines to specific users. **Rawsocket**
is not needed for BSC to function, however if you need this additional functionality
you will have to manually install the dependency with:

.. code-block:: bash 

    $ pip install rawsocket

Environment Configuration
-------------------------

AIT uses two environment variables for configuration.

**AIT_ROOT** is used for project wide pathing. If you don't set this AIT will attempt to do a good job of it for you. If you want to be safe you should set it to the project root where you checked out the code.  

**AIT_CONFIG** is used for locating the project's YAML configuration file. This environment variable should contain a full path to a valid **config.yaml** file. If you don't set this AIT will fail to initialize properly and will notify you that your configuration is invalid. If you wanted to set this to some example configuration that comes packaged with AIT you could set this to:

.. code-block:: bash

    /<project root path>/config/config.yaml

We recommend that you set this in your **postactivate** file from **virtualenvwrapper**. This will ensure that each time you activate the virtual environment that your **AIT_CONFIG** environment variable is set properly. By default, this file is located at **~/.virtualenvs/postactivate**.

.. code-block:: bash

   if [ $VIRTUAL_ENV == "$HOME/.virtualenvs/ait" ] 
   then
      export AIT_ROOT=/path/to/ait-core
      export AIT_CONFIG=/path/to/ait-core/config/config.yaml
   fi

Check Installation
------------------

Now that your installation has finished let's check that everything works as expected.

.. code-block:: bash

   # Deactivate your ait virtual environment
   $ deactivate

   # Reactivate your ait virtual environment to make sure we pick up the
   # new environment variable settings that you added
   $ workon ait

   # Test that you can properly import the ait.core package.
   $ python -c "import ait.core"

If the last command **doesn't** generate any errors your installation is all set! If you see an error as shown below make sure to activate your virtual environment first.

.. code-block:: bash

   $ python -c "import ait.core"
   Traceback (most recent call last):
     File "<string>", line 1, in <module>
   ImportError: No module named ait.core

If warnings of the format ``WARNING  | Config parameter <param> specifies nonexistant path <path>`` are printed, don't worry - this just means the default configurations are incorrect for the current state of your machine.

Working with AIT
----------------

Your AIT Core installation is now isolated to your virtual environment. Whenever you want to work on or run AIT related code run ``workon ait`` first to activate your environment. You will see a change in the format of your prompt indicating what environment you currently have active. If you want to disable the environment run ``deactivate``.

.. code-block:: bash

   # Normal prompt
   $

   # Prompt after running workon
   (ait)
   $

Upgrading an Installation
-------------------------

When a new version of AIT Core is released you'll most likely want to upgrade your environment. You'll need to upgrade differently depending on how you installed the system.

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

Run the following to upgrade to the latest AIT Core versions.

.. code-block:: bash

   $ pip install ait-core --upgrade
