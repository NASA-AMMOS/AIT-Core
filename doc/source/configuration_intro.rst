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
* **bsc**       - defines the location of the Binary Stream Capture (BSC) YAML configuration file.
* **logging**   - defines the name to be associated with the Logger component (defaults to 'bliss') and the host to push the output syslog information (defaults to 'localhost')
* **data**      - specifies all of the data paths associated with the GDS that can further be referenced by BLISS or mission-specific tools. The paths specified can use path variables to allow for value substitution
                  based upon date, hostname, platform, or any other configurable variable. See the *bliss-create-dirs* tool and *Path Expansion and Variables* section below for more details.

The filename paths should be considered relative to the location of **config.yaml**. If you have **hostname** specific configuration you can add another block of data. The **default** block is the fall back if a match cannot be found. Below is an example **config.yaml** file that defines the default configuration files for BLISS.

BLISS loads **config.yaml** on import.

Here is an example **config.yaml**:

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

        phase: 'dev'

        data:
            '1553':
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/downlink/1553
            bad:
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/downlink/bad
            lehx:
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/downlink/lehx
            planning:
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/planning
            sdos:
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/sdos
            uplink:
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/uplink
            ats:
                path: /gds/${phase}/data/${hostname}/${year}/${year}-${doy}/ats


If you want to look at the contents of **config.yaml** programmatically you can access it with:

    >>> bliss.config
    BlissConfig(...)

You can read more about each component's configuration and configuration-schema files in the component-specific pages.


Path Expansion and Variables
++++++++++++++++++++++++++++

File and directory paths included **config.yaml** can be specified with varying degrees of explicitness in order to allow for the most flexibility. Any file or directory path specified with a key of 'directory', 'file', 'filename', 'path', or 'pathname' will resolve according to the details below.

Absolute Path Expansion
_______________________

In the case where an absolute path is not specified for a 'file', 'filename', 'path', or 'pathname', the following are handled:

* path does not begin with '/' (relative path) - the path or filename given is assumed from the BLISS_CONFIG directory.
* path begins with '~' (User HOME directory)   - the current user's home directory is used

Variable Substitution
_____________________

Variables can also be specified within the path in order to allow for more explicit configuration. The following rules apply:

* Variables are extracted from the keys specified in the **config.yaml**.
* Any variables you would like to access must be at the base-level of the default, host, or platform:
.. code-block:: none

    default:
        phase:      'dev'
        mission:    'oco3'
        instrument: 'pma'

* The variable values must be a string or list of strings:
.. code-block:: none

    default:
        phase:      'dev'
        mission:    'oco3'
        instrument: ['pma', 'icc', 'ecc']

* Variables can be specified in a path using the following syntax
.. code-block:: none

    `${variable}`

    # For example
    path: /${phase}/${mission}/${instrument}

* There are currently 4 default variables whose values are automatically generated, and they can be access without specifying them in **config.yaml**.
  * ${year} - current year
  * ${doy}  - current day of year
  * ${hostname} - hostname of machine where GDS is running
  * ${platform} - platform of machine where GDS is running

Example
_______

If we have the following specified in **config.yaml**:
.. code-block:: none

    default:
        phase:      'dev'
        mission:    'oco3'
        data:
            data1:
                path: /${phase}/${hostname}/${year}-${doy}/data1
            data2:
                path: /${phase}/${hostname}/${year}-${doy}/data2

If the machine hostname = 'oco3-gds1', and today is day 300 in 2016, we can programmatically access these paths:
.. code-block:: python

    for k, v in bliss.config._datapaths.items():
         print "%s - %s" % (k ,v)

data1 - /dev/oco3-gds1/2016-300/data1
data2 - /dev/oco3-gds1/2016-300/data2


See *bliss-create-dir* software for more details on path substitution and how it can be leveraged.


YAML Idiosyncrasies
===================

While YAML is generally very user-friendly, every tool has its rough edges. The BLISS team has done its best to help you avoid these where possible. However, it may still be worth investigating potential roadblocks as you use YAML more. There is an excellent resource that the developers at SaltStack have put together on `YAML idosyncrasies <https://docs.saltstack.com/en/latest/topics/troubleshooting/yaml_idiosyncrasies.html>`_ that is worth reading. It should help you avoid any potential problems in your YAML configuration.

