AIT Database API
================

AIT provides a general database abstraction class on top of which custom implementations can be written. AIT comes packaged with abstractions for InfluxDB (:class:`ait.core.db.InfluxDBBackend`)and SQLite (:class:`ait.core.db.SQLiteBackend`). You can inherit from the abstract base class :class:`ait.core.db.GenericBackend` and implement your own database abstraction.

.. autoclass:: ait.core.db.GenericBackend
