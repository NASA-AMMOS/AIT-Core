Introduction to BLISS Command & Data Handling Tables and Products
=================================================================

The `bliss.core.table` module provides interfaces for encoding and decoding flight software tables to and from text and binary.

The flight software table formats are defined in YAML and usually stored in a configuration file called **table.yaml**. Tables are constructed from **header** definitions and **column** definitions.

.. code-block:: yaml

   --- !FSWTable
   name: OurTable
   delimiter: ","
   # other config

   header:
     - !FSWColumn
       name: FIRST_HEADER_COLUMN
       # other header column config

     - !FSWColumn
       name: SECOND_HEADER_COLUMN
       # other header column config

   columns:
     - !FSWColumn
       name: FIRST_COLUMN
       # other column config

     - !FSWColumn
       name: SECOND_COLUMN
       # other column config

There are a number of helper scripts for encoding/decoding flight software tables and for uploading tables. Checkout the :doc:`Command Line Intro <command_line>` page for additional information on what utilities are available. Each utility script provides information on its interfaces via **help** documentation.
