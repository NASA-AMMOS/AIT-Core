Limits Introduction
===================

The :class:`ait.core.limits` module provides support for specifying acceptable value ranges for telemetry fields.

Consider the below example telemetry packet and fields for which we'll specify limit values.

.. code-block:: YAML

   - !Packet
     name: 1553_HS_Packet
     desc: Ethernet 1553 packet used to monitor telemetry in real-time
     functions: CurrA_Fx(dn):   (dn - 2) / 1234.0

     fields:
       - !Field
         name: Voltage_A
         desc: Voltage A as a 14-bit DN.  Conversion to engineering units is TBD.
         units: Volts
         type: MSB_U16

       - !Field
         name: product_type
         type: U8
         enum:
           0: TABLE_FOO
           1: TABLE_BAR
           2: MEM_DUMP
           3: HEALTH_AND_STATUS

.. note::

   Limits are expected to be specified in Engineering Units when a given telemetry field has a corresponding DN-to-EU conversion. A field's value is converted via it's DN-to-EU function if present prior to limit checks.

Specifying Limits
-----------------

Limit values can be specified for fields with a value range and for fields with enumerated values. By default, limits are specified in **limits.yaml**. You can see the path specified in **config.yaml** under the **limits.filename** parameter.

.. code-block:: YAML

    limits:
        filename:  limits/limits.yaml

Value-Range Limits
^^^^^^^^^^^^^^^^^^

For the **1553_HS_PACKET.Voltage_A** field we'll specify min/max value ranges for our limits. You'll see in the example below that we're specifying upper and lower bounds with error and warning values for each. You can customize the limits as necessary by specify a subset of these values. For instance, you could specify just a lower warning bound if that is all you were concerned about.

.. code-block:: YAML

    - !Limit
      source: 1553_HS_Packet.Voltage_A
      desc: Voltage A
      units: Volts
      lower:
        error: 5.0
        warn: 10.0
      upper:
        error: 45.0
        warn: 40.0

Enum Limits
^^^^^^^^^^^

For fields with enumerated values, such as the **1553_HS_PACKET.product_type** field, we specify warning and error limits for one or more of the field's enumerated values. Here we're specifying an error limit when the field has the **MEM_DUMP** value and a warning limit when the field value is either **TABLE_FOO** or **TABLE_BAR**.

.. code-block:: YAML

    - !Limit
      source: 1553_HS_PACKET.product_type
      desc: Ethernet Product Type field
      value:
        error: MEM_DUMP
        warn:
          - TABLE_FOO
          - TABLE_BAR
