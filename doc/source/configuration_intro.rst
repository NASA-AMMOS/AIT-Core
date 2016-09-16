Introduction to BLISS Configuration
===================================

BLISS uses a number of `YAML <http://www.yaml.org/start.html>`_ (YAML Ain't Markup Language) and JSON files for project configuration.

In order to help BLISS properly configure your project, you should ensure that the *BLISS_CONFIG* environment variable points to your **config.yaml** file. Given the default BLISS project structure you would have the following setup. This assumes you've set *BLISS_ROOT* to the project's root directory::

    export BLISS_CONFIG=$BLISS_ROOT/data/config/config.yaml

What is YAML?
-------------

YAML is a data serialization language with a heavy focus on maintaining human-readability. The `YAML Getting Started <http://www.yaml.org/start.html>`_ provides an overview of the structures supported.

config.yaml
-----------

BLISS uses **config.yaml** to load configuration data for the command (cmddict), telemetry (tlmdict), Event Verification Record (evrdict), Binary Stream Capture (bsc), and Logging (logging) components.

* **cmddict**   - defines the location of the Command Dictionary YAML file
* **evrdict**   - defines the location of the Event Verification Record (EVR) Dictionary YAML file
* **tlmdict**   - defines the location of the Telemetry Dictionary YAML file
* **bsc** - defines the location of the Binary Stream Capture (BSC) YAML configuration file.
* **logging**   - defines the name to be associated with the Logger component (defaults to 'bliss') and the host to push the output syslog information (defaults to 'localhost')
* **gds_paths** - specifies all of the paths associated with the GDS that can further be referenced by BLISS or mission-specific tools. Year (YYYY) and day of year (DDD) can be included in the path and will be replaced by BLISS tools.

The filename paths should be considered relative to the location of **config.yaml**. If you have **hostname** specific configuration you can add another block of data. The **default** block is the fall back if a match cannot be found. Below is an example **config.yaml** file that defines the default configuration files for BLISS.

BLISS loads **config.yaml** on import.

Here is an example **config.yaml***:

.. code-block:: none

    default:
        cmddict:
            filename:  cmd.yaml

        evrdict:
            filename:  evr.yaml

        tlmdict:
            filename:  tlm.yaml

        bsc:
            filename:  bsc.yaml

        logging:
            name:      bliss
            hostname:  bliss.jpl.nasa.gov

        gds_paths:
            '1553':     /gds/dev/data/YYYY/DDD/downlink/1553
            bad:        /gds/dev/data/YYYY/DDD/downlink/bad
            lehx:       /gds/dev/data/YYYY/DDD/downlink/lehx
            planning:   /gds/dev/data/YYYY/DDD/planning
            sdos:       /gds/dev/data/YYYY/DDD/sdos
            uplink:     /gds/dev/data/YYYY/DDD/uplink
            ats:        /gds/dev/data/YYYY/DDD/ats/


If you want to look at the contents of **config.yaml** programmatically you can access it with:

    >>> bliss.config
    BlissConfig(...)

You can read more about each component's configuration and configuration-schema files in the component-specific pages.
