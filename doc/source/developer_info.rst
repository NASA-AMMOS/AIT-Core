Developer Documentation
=======================

Release Process
---------------

Prepare Repo for Release
^^^^^^^^^^^^^^^^^^^^^^^^

First you need to determine the version number for the release. **bliss-core** uses standard semantic versioning (Major.Minor.Patch). Major bumps are for large, non-backwards compatible changes; Minor bumps are for backwards compatible changes; Patch bumps are for incremental bug fixes, small releases, and end-of-sprint releases.

Update the project documentation to use the correct version names. The `conf.py <https://github.jpl.nasa.gov/bliss/bliss-core/blob/master/doc/source/conf.py>`_ file contains a **version** and **release** option. Both of these should be updated to point to the version number for this release. Commit and push these changes to master.

Generate Release Notes
^^^^^^^^^^^^^^^^^^^^^^

You will need a list of included tickets to put the in tag annotation when tagging the release. There is a helper script in /build that will generate this for you. Note that you can include a start and end time to help narrow down the notes to include since the last release made.

.. code-block:: bash

   cd build
   ./generate_changelog.py --start-time YYYY-MM-DDTHH:MM:SSZ

Tag the Release
^^^^^^^^^^^^^^^

Via the Github Releases page, draft a new release. Place the above version number as the tag version. The release title should be **BLISS v<version number>**. Copy the change log into the release description box. If the release is not product ready be sure to check the pre-release box to note that. When finished, publish the release.

Notify Relevant Parties of Release
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If deemed appropriate, prepare an email to all projects / parties known to be using the tool and notify them of a new release. An example template for this is below:

.. code-block:: none
   
   Subject:
   [ANNOUNCE][RELEASE] BLISS v<version> has been released
   
   Body:
   Hello!
   
   BLISS v<version> has been released and is ready for use.
   
   The following changes are included in this release:
   <paste change log here>
   
   You can download the release at:
   <link to release page>
   
   Thank you!
   BLISS Development Team
