AIT OpenMCT Plugin
========================

The *openmct* directory (AIT-Core/openmct/) contains files needed to expose AIT realtime and historical telemetry
endpoints to the OpenMCT framework.

This is a two step process:

* Activate the OpenMCT plugin within the AIT server configuration.  This step creates the data source from which OpenMCT will pull data.

* Deploy web-server with AIT-OpenMCT integration.  This step sets up a Node web-server for the OpenMCT framework that will access the AIT OpenMCT plugin service.



.. _Ait_openmct_plugin:

Activating the OpenMCT Plugin
-----------------------------

Update your AIT configuration file :ref:`config.yaml <Config_Intro>` to add the AITOpenMctPlugin in the 'server:plugins:' section.

.. _Ait_openmct_port:

The plugin's 'service_port' value defaults to 8082, but can be overridden in the configuration.  If something other than the default is used, you will also need to include this in the OpenMCT frameworks's setup configuration.

Currently, the server is assumed to run on 'localhost'.

.. _Plugin_config:

Example configuration with realtime telemetry only:

.. code-block:: none

    plugins:
        - plugin:
            name: ait.core.server.plugins.openmct.AITOpenMctPlugin
            inputs:
                - telem_stream
            service_port: 8082
            debug_enabled: False
            database_enabled: False



Example configuration with realtime and historical support:

.. code-block:: none

    plugins:
        - plugin:
            name: ait.core.server.plugins.openmct.AITOpenMctPlugin
            inputs:
                - telem_stream
            service_port: 8082
            debug_enabled: False
            database_enabled: True
            datastore: ait.core.db.InfluxDBBackend

**Note:**
When database is enabled, your AIT configuration file will also need to include a *database* section:

.. code-block:: none

    database:
         host: localhost
         port: 8086
         dbname: ait
         un: <username>
         pw: <password>



Integrating with OpenMCT Framework
----------------------------------

**Note:**
Earlier versions of the AIT-OpenMCT integration required explicit
installation of OpenMCT, and adding AIT extensions to that deployment.
This has since been simplified where OpenMCT is now treated as a dependency.

**Note:**
The AIT extension requires 'http.js', a library that was
included in the OpenMCT Tutorial (Apache License, Version 2.0).
The source location of this file is:
https://github.com/nasa/openmct-tutorial/tree/completed/lib/http.js
It is currently included with our example OpenMCT server.


Server Setup
^^^^^^^^^^^^^^

While treating OpenMCT as a dependency, a Node web-server capable of running
the OpenMCT service is still needed.  AIT provides a basic example
server which fulfills this need (based on the OpenMCT tutorial).
See `AIT-Core/openmct/example-server
<https://github.com/NASA-AMMOS/AIT-Core/tree/master/openmct/example-server>`_.

The example server includes:

* *package.json* - with all dependencies, including OpenMCT; and service launcher.

* *server.js* - entry point for the web-server that will host OpenMCT service.

* *index.html* - sets up OpenMCT and AIT extensions.

* *lib/http.js* - modified library required by the integration.

* *ait_integration.js* - symlink to AIT-OpenMct service integration.


**Setup steps:**

Are steps assume you will be setting up the web-server in a directory identified by $OPENMCT_DIR

1. Copy *example-server* to a directory referenced by *$OPENMCT_DIR*

.. code-block:: none

    cp -RL ./example-server $OPENMCT_DIR  #Recursive copy, resolve symlinks to real files


2) Install service dependencies (including OpenMCT) via NPM and package.json:

.. code-block:: none

    cd $OPENMCT_DIR
    npm install


**Running steps:**

The web-server can be launched via Node-NPM:

.. code-block:: none

     npm start

Notes on the OpenMCT Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The index.html includes the import of the required Javascript files:

.. code-block:: none

        <script src="lib/http.js"></script>
        <script src="ait_integration.js"></script>


...as well as the OpenMCT installation of the AIT integration and data endpoints:

.. code-block:: none

         openmct.install(AITIntegration({
                 host: 'localhost',
                 port : 8082 }));
         openmct.install(AITHistoricalTelemetryPlugin());
         openmct.install(AITRealtimeTelemetryPlugin());

**Note:** If you change the AIT-OpenMCT plugin's *service_port* in your AIT config, the same value should be used for the *port* above.



Running AIT / OpenMCT
---------------------

1) Start the AIT server (configured to run AIT's OpenMct plugin)
2) Start OpenMCT server  (npm start)
3) Open browser to location of the OpenMCT UI endpoint.
