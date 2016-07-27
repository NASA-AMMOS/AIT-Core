Introduction to BLISS Configuration
===================================

BLISS uses a number of `YAML <http://www.yaml.org/start.html>`_ (YAML Ain't Markup Language) and JSON files for project configuration.

In order to help BLISS properly configuration your project, you should ensure that the *BLISS_CONFIG* environment variable to your **config.yaml** file. Given the default BLISS project structure you would have the following setup. This assumes you've set *BLISS_ROOT* to the project's root directory::

    export BLISS_CONFIG=$BLISS_ROOT/data/config/config.yaml

What is YAML?
-------------

YAML is a data serialization language with a heavy focus on maintaining human-readability. the `YAML Getting Started <http://www.yaml.org/start.html>`_ provides an overview of the structures supported.

config.yaml
-----------

BLISS uses **config.yaml** to load configuration data for the command, telemetry, Event Verification Record, and Binary Stream Capture components. The filename paths for each component should be considered relative to the location of **config.yaml**. If you have **hostname** specific configuration you can add another block of data. The **default** block is the fall back if a match cannot be found. Below is an example **config.yaml** file that defines the default configuration files for BLISS.

.. code-block:: none

    default:
        cmddict:
            filename:  cmd.yaml

        evrdict:
            filename:  evr.yaml

        tlmdict:
            filename:  tlm.yaml

        bsc:
            filename: bsc.yaml

You can read more about each component's configuration and configuration-schema files in the component-specific pages. 
