Packet Accumulator Plugin
========================
The Packet Accumulator plugin accumulates pipeline data.
The accumulated packets are not published to the next pipeline stage until one of two conditions are met:

#. The periodic timer defined by *timer_seconds* has triggered.
#. The accumulated packets are large enough that the next packet will not fit without exceeding *max_size_octets*

Configuration
^^^^^^^^^^^^^
Add the following template to the plugins block of your config.yaml and customize as necessary.

.. code-block:: none
    - plugin:
      name: ait.core.server.plugins.PacketAccumulator.PacketAccumulator
      inputs:
          - command_stream
      timer_seconds: 1
	  max_size_octets: 1024

Limitations
^^^^^^^^^^^
This plugin can not split a packet set across two accumulations.
Any packet whose addition would cause the currently accumulation size to exceed *max_size_octets* will be put in a new accumulation.
