Packet Padder Plugin
========================
The packet padder plugin pads command processing pipeline data to a user configured size in octets.

If the size of pipeline data in octets is less than the user specified value, the pipline will pad 0s to achieve the specified size.

Configuration
-------------

Add and customize the following template in your config.yaml

.. code-block:: none

	- plugin:
          name: ait.core.server.plugins.PacketPadder.PacketPadder
          inputs:
	          - PacketAccumulator
          pad_octets: 987

The *pad_octets* option specifies the minimum size to pad the data to. The plugin will not modify the data if its size already meets or exceeds this value. A negative, 0, or missing value will bypass the plugin.

Use *inputs* to specify which PUB/SUB topic the plugin should receive pipeline data from.
