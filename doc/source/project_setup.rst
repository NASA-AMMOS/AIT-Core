Setting up a New Project with BLISS
===================================

The following documentation will teach you how to setup a new project to build off of the BLISS toolkit. This guide assumes that the project you'll be developing is a Python-based project.

Add BLISS Core as a Dependency
------------------------------

You'll need to add BLISS Core to either your **requirements.txt** file or your **setup.py** file.

If you use a requirements file for specifying dependencies:

.. code-block:: bash

   --extra-index-url https://bliss.jpl.nasa.gov/pypi/simple/
   bliss-core==1.0.0

If you use **setup.py** for specifying dependencies:

.. code-block:: bash

   install_requires = [
       bliss-core==1.0.0
   ],
   dependency_links = [
       'https://bliss.jpl.nasa.gov/pypi/simple/bliss-core/'
   ]

Set BLISS Config Values
-----------------------

BLISS provides a large number of configuration parameters for customizing and configuring the toolkit. BLISS ships with an example **config.yaml** skeleton located at **/PROJECT_ROOT/data/config/config.yaml** that you can use as a baseline configuration file. You should read the :doc:`Configuration Introduction <configuration_intro>` and the component specific configuration documents such as the :doc:`Telemetry <telemetry_intro>`, :doc:`Commanding <command_intro>`, and :doc:`EVR <evr_intro>` pages for additional information and update the files to meet your projects specifications.
