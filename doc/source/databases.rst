AIT Database API
================

AIT provides a general database abstraction class on top of which custom implementations can be written. AIT comes packaged with abstractions for InfluxDB (:class:`ait.core.db.InfluxDBBackend`)and SQLite (:class:`ait.core.db.SQLiteBackend`). You can inherit from the abstract base class :class:`ait.core.db.GenericBackend` and implement your own database abstraction.

The Data Archive Plugin, which is provided as part of AIT-Core at :class:`ait.core.server.plugins.DataArchive`, uses this database backend for archiving incoming data. It uses the :class:`ait.core.db.InfluxDBBackend` by default, but a custom database can be implemented and used instead by specifying the ``datastore`` parameter in the plugin's configuration.
