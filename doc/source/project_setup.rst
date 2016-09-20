Setting up a New Project with BLISS
===================================

This guide will show you how to setup a new project building off of BLISS. It assumes your project dependencies are installed into a virtual environment.

Set BLISS as a Dependency
-------------------------

In your current project's requirements file you need to add the latest version of BLISS. You can do this two ways, directly from the repository or from a downloaded copy of the source.

Clone from the Main Repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::

   This will fail to work if you don't have SSH keys setup in the main repository. As such, if you arne't a contributor to bliss-core you should scope other methods.

Add the following to your requirements/setup file. Note that the below example is for v0.1.0, you should update this to grab the latest version of the code.

.. code-block:: bash

   git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@0.1.0#egg=bliss-core

Downloaded Source
^^^^^^^^^^^^^^^^^

Download the latest code .zip file from the `project's releases page <https://github.jpl.nasa.gov/bliss/bliss-core/releases>`_.

Add the following to your requirements/setup file (updating the path and version number as appropriate).

.. code-block:: bash

   /path/to/bliss-core-0.1.0.zip

Update Installed Requirements
-----------------------------

You'll need to reinstall your requirements so **bliss-core** and its dependencies are installed.

If you're using a requirements file:

.. code-block:: bash

   pip install -r /path/to/requirements.txt

If you're using a setup.py file:

.. code-block:: bash

   # From the project root
   pip install -e .

Set BLISS Config Values
-----------------------

BLISS provides a number of default configuration files as an example for you to build off of. You should read the :doc:`Telemetry <telemetry_intro>` and :doc:`Commanding <command_intro>` pages for additional information and update the files to meet your projects specifications.

You will also need to point BLISS to your configuration. Assuming you have placed the config in *<project root>/config* you need to set:

.. code-block:: bash

   export BLISS_CONFIG=<project root>/config/config.yaml
