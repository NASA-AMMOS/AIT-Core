Onboard Tables and Products
===========================

The `ait.core.table` module provides interfaces for encoding and decoding flight software tables to and from text and binary.

The flight software table formats are defined in YAML and usually stored in a configuration file called **table.yaml**. Tables are constructed from **header** definitions and **column** definitions.

.. code-block:: yaml

    - !FSWTable
      name: TestTable
      delimiter: ","
      uptype: 1
      size: 18
      header:
        - !FSWColumn
          name: uptype
          desc: This table's `uptype` field for use when decoding
          type: U8

        - !FSWColumn
          name: HEADER_COLUMN_TWO
          desc: The second column in our header
          type:  U8

        - !FSWColumn
          name: HEADER_COLUMN_THREE
          desc: The third column in our header
          type:  U8

      columns:
        - !FSWColumn
          name: COLUMN_ONE
          desc: First FSW Table Column
          type:  MSB_U16

        - !FSWColumn
          name: COLUMN_TWO
          desc: Second FSW Table Column
          type:  MSB_U16

        - !FSWColumn
          name: COLUMN_THREE
          desc: Third FSW Table Column
          type:  U8
          enum:
            0: TEST_ENUM_0
            1: TEST_ENUM_1
            2: TEST_ENUM_2
            3: TEST_ENUM_3


AIT Core's table support attempts to cover a baseline use case that demonstrates helpful functionality and which project's will hopefully find useful. However, much like Command encoding, it's very likely that projects will need to adapt Core table classes and utilities to meet their needs. We'll discuss the components of table configuration, how Core uses / exposes them by default, and how to customize for project-specific use cases.


Default Table Handling
----------------------

The default table handling assumes a few things discussed below. It's likely this won't be exactly what your project expects. We'll cover adaptations in a second.

- An encoded table is always a fixed size. This size (in bytes) is called out in the **size** attribute of a **!FSWTable**. When encoding a table, if the resulting binary blob is less than the **size** specified it is zero padded. If it's larger, it fails. 
- Text versions of a table are "delimiter separated files" where the **delimiter** attribute of a **!FSWTable** specifies that is.
- Tables always have a header and a table-type-specific-identifier is always encoded as the first byte. This value is expected to match the **uptype** specified on one of the **!FSWTable** definitions.

Encoding a row in a table (including the header) is done by encoding a column's value according to the **type** specified for that **!FSWColumn**. Decoding is the inverse, decoding a slice of that table's data according to the **type** specified for that **!FSWColumn**.


Customizing
-----------

Project-specific adaptation focuses around four main elements:

- :class:`ait.core.table.FSWTabDefn` handles encoding / decoding of tables (via :func:`ait.core.table.FSWTabDefn.encode` and :func:`ait.core.table.FSWTabDefn.decode` respectively).
- :class:`ait.core.table.FSWColDefn` handles encoding / decoding of columns. 
- The CLI utilities **ait-table-encode** and **ait-table-decode**.

:class:`ait.core.table.FSWColDefn` encoding and decoding are largely wrappers around the Core :mod:`ait.core.dtype` functionality for doing the same. Unless you want to completely change how data types are dealt with in your tables you probably won't need to customize **FSWColDefn**. The CLI utilities **ait-table-[encode|decode]** are both minimal wrappers around calls to :class:`ait.core.table.FSWTabDefn` encode and decode functions. They're mostly boilerplate for handling arguments, checking file paths, etc., and can be easily rewritten to serve your projects use cases.

:class:`ait.core.table.FSWTabDefn` handles the heavy lifting via :func:`ait.core.table.FSWTabDefn.encode` and :func:`ait.core.table.FSWTabDefn.decode`. The interfaces for these functions are generic (taking only **\*\*kwargs**) so users can define the interface in nearly whatever form they'd like. Creating an extension of **FSWTabDefn** and overwriting the encode and decode functions is likely the minimum that your project will need.

----


!FSWTable
---------

name:
    A **string** name for this table.

delimiter:
    A **string** denoting the column separator for this table.

uptype:
    A table-unique identifier.

size:
    The **exact** size of an encoded version of this table in bytes.

header:
    A **list** of **!FSWColumn** entries defining the structure of the table's header.

columns:
    A **list** of **!FSWColumn** entries defining the structure of a row of table data.


!FSWColumn
----------

name:
    A **string** name for this column.

type:
    A :mod:`ait.core.dtype`-defined data type specifying the format of this column.

desc (optional):
    A **string** for providing a description of the column.

enum (optional):
    A mapping of column values to human-readable enumeration values.

