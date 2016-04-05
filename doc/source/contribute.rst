Contributor Guides
==================

Installation
------------

Before you install **bliss-core** you should install `virtualenv <https://virtualenv.pypa.io/en/latest/installation.html>`_ to properly isolate your development environment. It is also recommended that you install `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_ for convenience. The following instructions will assume that you have installed both already.

Installation is largely the same if you wish to contribute or make changes to the code compared to simply using the toolkit. The only real change is installing **bliss-core** as a "develop" mode package so we can make changes and test them without needing to reinstall the changed files.

.. code-block:: bash

    $ pip install -e .[docs,tests]

Project Workflow Overview
-------------------------

AIT use a feature-branch / pull request approach to organizing contributions to the toolkit. All code is reviewed prior to integration into the toolkit.

Track changes via tickets
^^^^^^^^^^^^^^^^^^^^^^^^^

All changes need to be made against one or more tickets for tracking purposes. AIT uses Github Issues along with Zenhub to track issue in the project. All tickets should have (outside of rare edge-cases):

- A concise title
- An in-depth description of the problem / request. If reporting a bug, the description should include information on how to reproduce the bug. Also include the version of the code where you're seeing the bug.

If you're going to begin work on a ticket make sure to progress the ticket through the various **Pipeline** steps as appropriate as well as assigning yourself as an **Assignee**. If you lack sufficient permissions to do so you can post on the ticket asking for the above to be done for you.

Commit Messages
^^^^^^^^^^^^^^^

AIT projects take a fairly standard approach to commit message formatting. You can checkout `Tim Pope's blog <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_ for a good starting point to figuring out how to format your commit messages. All commit messages should reference a ticket in their title / summary line.

.. code-block:: none

   Issue #248 - Show an example commit message title

This makes sure that tickets are updated on Github with references to commits that are related to them.

Pull Requests and Feature Branches
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All changes should be isolated to a feature branch that links to a ticket. The standard across AIT projects is to use **issue-###** for branch names where **###**  is the issue number found on Github.

The title of a pull request should include a reference to the ticket being fixed as mentioned for commit messages. The description of a pull request should provide an in-depth explanation of the changes present. Note, if you wrote good commit messages this step should be easy!

Any tickets that are resolved by the pull request should be referenced with Github's syntax for closing out tickets. Assuming the above ticket we would have the following in a pull request description:

.. code-block:: none

   Resolve #248

Documentation
-------------

AIT uses Sphinx to build its documentation. You can build the documentation
with:

.. code-block:: bash

    $ python setup.py build_sphinx

To view the documentation, open **doc/build/html/index.html** in a web browser.

If you need to update the auto-generated documentation you can run the
following command to rebuild all of the **bliss** package documentation:

.. code-block:: bash

    $ sphinx-apidoc --separate --force --no-toc -o doc/source bliss bliss/test

Please make sure to update the docs if changes in a ticket result in the
documentation being out of date.

Unit Tests
----------

AIT uses the `Nose <https://nose.readthedocs.org/en/latest/>`_ unit
test framework.  To run the tests in **python/bliss/test**:

.. code-block:: bash

    $ python setup.py nosetests

Please be sure to check that all tests pass before creating a pull request for a ticket. All new functionality or changes to existing functionality should include one or more (probably more) tests covering those changes.

Coding Style
------------

AIT makes a best-effort attempt at sticking with PEP-8 conventions.

Mailing Lists
-------------

The AIT mailings lists are a good way to get in contact with people working on the project. If you need help with something on the project feel free to send an email to the AIT team at **bliss.support@jpl.nasa.gov**.

Slack Channels
--------------

AIT has three channels on the JPL team Slack. Generic AIT conversations happen on **#bliss**, development conversations happen on **#bliss-development**, and user support conversations happen on **#bliss-support**.

