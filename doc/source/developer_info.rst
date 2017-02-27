Developer Documentation
=======================

Release Process
---------------

Prepare Repo for Release
^^^^^^^^^^^^^^^^^^^^^^^^

First you need to determine the version number for the release. **bliss-core** uses standard semantic versioning (Major.Minor.Patch). Major bumps are for large, non-backwards compatible changes; Minor bumps are for backwards compatible changes; Patch bumps are for incremental bug fixes, small releases, and end-of-sprint releases.

Update the project documentation to use the correct version names. The `conf.py <https://github.jpl.nasa.gov/bliss/bliss-core/blob/master/doc/source/conf.py>`_ file contains a **version** and **release** option. Both of these should be updated to point to the version number for this release. The appropriate version number must also be set in the project's **setup.py** file. Commit and push these changes to master.

Generate Release Notes
^^^^^^^^^^^^^^^^^^^^^^

You will need a list of included tickets to put the in tag annotation when tagging the release. There is a helper script in /build that will generate this for you. Note that you can include a start and end time to help narrow down the notes to include since the last release made.

.. code-block:: bash

   cd build
   ./generate_changelog.py --start-time YYYY-MM-DDTHH:MM:SSZ

Tag the Release
^^^^^^^^^^^^^^^

Via the Github Releases page, draft a new release. Place the above version number as the tag version. The release title should be **BLISS v<version number>**. Copy the change log into the release description box. If the release is not production ready be sure to check the pre-release box to note that. When finished, publish the release.

Push Latest Docs to Github Pages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You will need to push the latest documentation to Github pages for the release. There is a script that helps you with the majority of this.

.. code-block:: bash

   cd build
   ./update_docs_release.sh
   git status # Check that everything looks correct
   git commit -m "Update docs for <version>"
   git push origin gh-pages

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

Push Release Artifacts to OCO3-TB PyPi
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SSH into OCO3-TB and navigate to **/usr/local/vhosts/oco3-tb/htdocs/pypi**. Open **make-pypi.sh** and update with the new version number and comment out the previous number. Run **make-pypi.sh** and check https://bliss.jpl.nasa.gov/pypi/simple/ to ensure that the release has been added.


Pointing to a Release
---------------------

To use BLISS in your project you'll want to point to a specific release in your project's requirements file. We recommending installing all project dependencies into a virtualenv environment to ensure a properly isolated Python environment. You can specify a BLISS release in your **requirements.txt** file with the below snippet. You should replace the version number as appropriate.

.. code-block:: none

   git+ssh://git@github.jpl.nasa.gov/bliss/bliss-core.git@<version # here>#egg=bliss-core[tests,docs]

If you have access to the OCO-TB machine you can use our PyPi server for pulling down the dependency. Use the following line to set your bliss-core dependency to the latest available:

.. code-block:: none

    --extra-index-url https://bliss.jpl.nasa.gov/pypi/simple/ bliss-core


Upgrading an Existing Environment
---------------------------------

When a new BLISS release is pushed you will most likely want to upgrade the dependency for any projects that build off of BLISS. You'll want to update the project's requirement file to point to the new release. You can then install / update dependencies with:

.. code-block:: bash

   pip install -r requirements.txt --upgrade

Installing from a Downloaded Release
------------------------------------

If you prefer to install releases from downloaded source (or are required to for technical reasons), you can download the relevant release from the `BLISS release page <https://github.jpl.nasa.gov/bliss/bliss-core/releases>`_ when a new release is made available. Un-zip or un-tar the file and run the following command from the root of the release folder:

.. code-block:: bash

   pip install . --upgrade
