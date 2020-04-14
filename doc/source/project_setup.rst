Setting up a New Project with AIT
=================================

The following documentation will teach you how to setup a new project to build off of the AMMOS Instrument Toolkit. This guide assumes that the project you'll be developing is a Python-based project.

.. note::  AIT is tested against *Python 3.7*.  Running AIT with other versions of *Python 3* may have issues.

Add AIT Core as a Dependency
------------------------------

You'll need to add AIT Core to either your **requirements.txt** file or your **setup.py** file.

If you use a requirements file for specifying dependencies:

.. code-block:: bash

   ait-core==1.0.0

If you use **setup.py** for specifying dependencies:

.. code-block:: bash

   install_requires = [
       ait-core==1.0.0
   ],

Set AIT Config Values
---------------------

AIT provides a large number of configuration parameters for customizing and configuring the toolkit. AIT ships with an example **config.yaml** skeleton located at **/PROJECT_ROOT/config/config.yaml** that you can use as a baseline configuration file. You should read the :doc:`Configuration Introduction <configuration_intro>` and the component specific configuration documents such as the :doc:`Telemetry <telemetry_intro>`, :doc:`Commanding <command_intro>`, and :doc:`EVR <evr_intro>` pages for additional information and update the files to meet your project's specifications.
