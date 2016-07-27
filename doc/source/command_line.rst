BLISS Command Line Utilities
============================

BLISS provides a number of command line utilities from performing common operations and component initialization. Below is a breakdown of these utilities with a brief explanation of how they work and why you my use them.

----

Component Initialization Utilities
----------------------------------

The following commands are used to start up BLISS services or components.

bliss-bsc
^^^^^^^^^

Starts up the Binary Stream Capture components along with a webserver for manipulation of active capture handlers via a RESTful interface. For additional information on ``bliss.bsc`` usage and configuration check out the :doc:`BSC Introduction <bsc_intro>` page.

bliss-gui
^^^^^^^^^

Start up the BLISS GUI and opens your browser to the primary landing page.

----

Sequence Utilities
------------------

Utilities for the manipulation of command sequences.

bliss-seq-encode
^^^^^^^^^^^^^^^^

Encodes a given command sequence file into binary.

bliss-seq-decode
^^^^^^^^^^^^^^^^

Decodes a given command sequence binary blob into a text file.

bliss-seq-send
^^^^^^^^^^^^^^

Sends a given command sequence to a UDP port. This is useful for uploading command sequences to simulators.

bliss-seq-print
^^^^^^^^^^^^^^^

Pretty print a given command sequence binary blob to standard out.

----

Telemetry Utilities
-------------------

bliss-tlm-send
^^^^^^^^^^^^^^

Upload a given telemetry PCap file to a UDP port. This is useful for uploading telemetry to simulators.

----

Command Utilities
-----------------

bliss-cmd-send
^^^^^^^^^^^^^^

Send a given command and its arguments to a UDP port. This is useful for uploading commands to simulators.

----

Miscellaneous Utilities
-----------------------

bliss-orbits
^^^^^^^^^^^^

Generates predicted or actual ISS orbit times and numbers given JSC ISS Attitutde and Pointing Nadir reports or ISS Ephemeris data.

bliss-zlip-upload
^^^^^^^^^^^^^^^^^

Compresses and uploads a file to the ISS Simulator. This is primarily used for Flight Software Testing.

bliss-yaml-validate
^^^^^^^^^^^^^^^^^^^

Validates YAML files against an applicable schema. This is useful for ensuring that your YAML configuration files match the expected schema.
