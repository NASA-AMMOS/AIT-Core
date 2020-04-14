AIT OpenMCT Plugin
========================

The 'openmct' directory (AIT-Core/openmct/) contains files needed by your
OpenMCT installation that will expose AIT realtime and historical telemetry
endpoints to the OpenMCT framework.

There is a two step process:

* Activate the OpenMCT plugin within the AIT server configuration.  This step creates the data source from which OpenMCT will pull data.

* Integrate AIT extensions in OpenMCT.  This step installs Javascript extensions into the OpenMCT framework that will access the AIT OpenMCT plugin service.


.. _Ait_openmct_plugin:

Activating the OpenMCT Plugin
-----------------------------

Update your AIT configuration file :ref:`config.yaml <Config_Intro>` to add the AITOpenMctPlugin in the 'server:plugins:' section.

.. _Ait_openmct_port:
The plugin's 'port' value defaults to 8082, but can be overridden in the configuration.  If something other than the default is used, you will also need to include this in
the OpenMCT frameworks's setup configuration.

Currently, the server is assumed to run on 'localhost'.

.. _Plugin_config:

Example configuration:

.. code-block:: none

    plugins:
        - plugin:
            name: ait.core.server.plugins.openmct.AITOpenMctPlugin
            inputs:
                - telem_stream
            port: 8082



Integrating with OpenMCT Framework
----------------------------------

**Note:**
At this time, the AIT-Integration is capatible with OpenMCT  v0.14.0.  Setup step 1 will address this.

**Note:**
The AIT extension requires 'http.js', a library that was included in the OpenMCT Tutorial (Apache License, Version 2.0).
The source location of this file is: https://github.com/nasa/openmct-tutorial/tree/completed/lib/http.js


Setup
^^^^^

1. Install OpenMCT (https://nasa.github.io/openmct/getting-started/)

To ensure you get the capatible version of the software, after performing the git-clone step, you will need to checkout the v0.14.0 version.

.. code-block:: none

    git clone https://github.com/nasa/openmct.git   #Download OpenMCT
    git checkout v0.14.0                            #Checkout required version
    npm install                                     #Install dependencies


We will assume that OpenMCT is installed in a directory referenced
by the environment variable ${OPENMCT_DIR}


2. Copy the downloaded 'http.js' library file to your OpenMCT installation:

.. code-block:: none

    mkdir ${OPENMCT_DIR}/lib
    cp http.js ${OPENMCT_DIR}/lib/


3. Copy the 'ait_integration.js' file to your OpenMCT installation:

.. code-block:: none

    cp ait_integration.js ${OPENMCT_DIR}


4. Edit the existing OpenMCT 'index.html' file to include references to the 'http.js' and 'ait_integration.js' (prior
to the script tag that initializes OpenMCT):

.. code-block:: none

        <script src="lib/http.js"></script>
        <script src="ait_integration.js"></script>


5. Install AIT extensions to the openmct framework (prior to the openmct.start() function call).  Value of 'port' should match the value used in the :ref:`previous section<Ait_openmct_plugin>`.

.. code-block:: none

        openmct.install(AITIntegration({
                host: 'localhost',
                port : 8082 }));
        openmct.install(AITHistoricalTelemetryPlugin());
        openmct.install(AITRealtimeTelemetryPlugin());




Running AIT / OpenMCT
---------------------

1) Start the AIT server (configured to run AIT's OpenMct plugin)
2) Start OpenMCT server  (npm start)
3) Open browser to location of the OpenMCT UI endpoint.

