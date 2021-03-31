AIT Database API
================

Database Backends
-----------------

AIT provides a general database abstraction class on top of which custom implementations can be written. AIT comes packaged with abstractions for InfluxDB (:class:`ait.core.db.InfluxDBBackend`)and SQLite (:class:`ait.core.db.SQLiteBackend`). You can inherit from the abstract base class :class:`ait.core.db.GenericBackend` and implement your own database abstraction.

.. warning::

   Note, the database-specific implementations of :class:`ait.core.db.GenericBackend` will often require
   a custom field to be inserted to track time associated with a given packet or field value. In general,
   AIT-provided implementations use **time** for the name of this field. User defined Packet Fields should
   avoid using this name. If an implementation uses a different value it will be noted for that specific
   backend.

.. autoclass:: ait.core.db.GenericBackend
   :members:
   :undoc-members:
   :show-inheritance:


Data Archive Plugin
-------------------

The Data Archive Plugin, which is provided as part of AIT-Core at :class:`ait.core.server.plugins.DataArchive`, uses the database backend APIs for archiving incoming data. It uses the :class:`ait.core.db.InfluxDBBackend` by default, but a custom database can be implemented and used instead by specifying the ``datastore`` parameter in the plugin's configuration.

.. code::

   plugins:
       - plugin:
           name: ait.core.server.plugins.DataArchive
           inputs:
               - log_stream
           datastore:
               ait.core.db.InfluxDBBackend

.. autoclass:: ait.core.server.plugins.DataArchive
   :members:
   :undoc-members:
   :show-inheritance:
