
.. image:: https://github.com/NASA-AMMOS/AIT-Core/actions/workflows/full_build.yaml/badge.svg?branch=master
   :target: https://github.com/NASA-AMMOS/AIT-Core/actions
   :alt: Build and Lint Status

.. image:: https://readthedocs.org/projects/ait-core/badge/?version=latest
    :target: https://ait-core.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

The AMMOS Instrument Toolkit (Formerly the Bespoke Links to Instruments
for Surface and Space (BLISS)) is a Python-based software suite
developed to handle Ground Data System (GDS), Electronic Ground Support
Equipment (EGSE), commanding, telemetry uplink/downlink, and sequencing
for instrument and CubeSat Missions. It is a generalization and expansion
of tools developed for a number of ISS
missions.

Getting Started
===============

You can read through the `Installation and Configuration
Page <http://ait-core.readthedocs.io/en/latest/installation.html>`__ for
instruction on how to install AIT Core.

You can read through the `New Project Setup
Page <http://ait-core.readthedocs.io/en/latest/project_setup.html>`__
for instructions on how to use AIT on your next project.

Join the Community
==================

The project's `User and Developer Mailing List <https://groups.google.com/forum/#!forum/ait-dev>`__ is the best way to communicate with the team, ask questions, brainstorm plans for future changes, and help contribute to the project.

This project exists thanks to the dedicated users, contributors, committers, and project management committee members. If you'd like to learn more about how the project is organized and how to become a part of the team please check out the `Project Structure and Governance <https://github.com/NASA-AMMOS/AIT-Core/wiki/Project-Structure-and-Governance>`__ documentation.

Contributing
============

Thank you for your interest in contributing to AIT! We welcome contributions from people of all backgrounds and disciplines. While much of the focus of our project is software, we believe that many of the most critical contributions come in the form of documentation improvements, asset generation, user testing and feedback, and community involvement. So if you're interested and want to help out please don't hesitate! Send us an email on the public mailing list below, introduce yourself, and join the community.

Communication
-------------
All project communication happens via mailing lists. Discussions related to development should happen on the public `Developer and User Mailing List <https://groups.google.com/forum/#!forum/ait-dev>`__. If you're new to the community make sure to introduce yourself as well!

Dev Installation
----------------
As always, we encourage you to install AIT into a virtual environment of your choosing when you set up your development environment. AIT uses `poetry` for package management. Before setting up your development environment you will need the following installed and ready to use:

- A virtual environment "manager" of your choosing with a configured and activated virtual environment. Since AIT uses `poetry` you can consider leveraging its `environment management <https://python-poetry.org/docs/managing-environments/>`__ functionality as well.
    - Using `poetry shell` is also very convenient for development testing and simplifying environment management. You should make sure to install the package into the shell to get access to the development dependencies as well. It's recommended that you use `poetry shell` when running the tox builds because other virtual environment managers will often prevent tox from accessing `pyenv`-installed Python versions.
- `pyenv <https://github.com/pyenv/pyenv>`__ so you can easily install different Python versions
- `poetry <https://python-poetry.org/docs/#installation>`__ installed either to your specific virtual environment or system-wide, whichever you prefer.

Install the package in "editable" mode with all the development dependencies by running the following::

    poetry install

As with a normal installation you will need to point `AIT_CONFIG` at the primary configuration file. You should consider saving this in your shell RC file or your virtual environment configuration files so you don't have to reset with every new shell::

    export AIT_CONFIG=/path/to/ait-core/config/config.yaml

You should configure `pre-commit` by running the following. This will install our pre-commit and pre-push hooks::

    pre-commit install && pre-commit install -t pre-push

Finally, you should install the different Python versions that the project supports so they're accessible to `tox`. Using `pyenv` is the easiest way to accomplish this::

    cat .python-version | xargs -I{} pyenv install --skip-existing {}

Dev Tools
---------

Tox
~~~
Use `tox` to run a thorough build of the toolkit that checks test execution across different Python versions, verifies the docs build, runs the linting pipeline, and checks that the repo packages cleanly. Make sure you run `tox` in Poetry's `shell` without another virtual environment active to avoid problems with `tox` finding different python versions for the tests. You can run all of the development tools with::

    tox

You can see the available `tox` test environments by passing `-l` and execute a specific one by passing its name to `-e`. Run `tox -h` for more info.

Tests
~~~~~

Use `pytest` to manually run the test suite::

    pytest

Or via `tox` for a specific python version::

    tox -e py310


Code Checks
~~~~~~~~~~~
We run ``black``, ``flake8``, ``mypy``, and a few other minor checkers on the code base. Our linting and code check pipeline is run whenever you commit or push. If you'd like to run it manually you can do so with the following::

    pre_commit run --color=always {posargs:--all}

Individual calls to the tools are configured in ``.pre-commit-config.yaml``. If you'd like to run a specific tool on its own you can see how we call them there.

You can run all the linting tools with tox as well::

    tox -e lint


Documentation
~~~~~~~~~~~~~

AIT uses Sphinx to build its documentation. You can build the documentation with::

    poetry run build_sphinx

To view the documentation, open ``doc/build/html/index.html`` in a web browser. If you just want to check that the docs build is working you can use tox::

    tox -e docs

If you need to update the auto-generated documentation you can run the following command to rebuild all of the package documentation::

    sphinx-apidoc --separate --force --no-toc -o doc/source ait --implicit-namespaces

Please make sure to update the docs if changes in a ticket result in the documentation being out of date.


Project Workflow
----------------
Issue Tracking
~~~~~~~~~~~~~~
All changes need to be made against one or more tickets for tracking purposes. AIT uses GitHub Issues along with Zenhub to track issue in the project. All tickets should have (outside of rare edge-cases):

- A concise title
- An in-depth description of the problem / request. If reporting a bug, the description should include information on how to reproduce the bug. Also include the version of the code where you’re seeing the bug.

If you’re going to begin work on a ticket make sure to progress the ticket through the various Pipeline steps as appropriate as well as assigning yourself as an Assignee. If you lack sufficient permissions to do so you can post on the ticket asking for the above to be done for you.

Commit Messages
~~~~~~~~~~~~~~~
AIT projects take a fairly standard approach to commit message formatting. You can checkout Tim Pope's blog for a good starting point to figuring out how to format your commit messages. All commit messages should reference a ticket in their title / summary line::

    Issue #248 - Show an example commit message title

This makes sure that tickets are updated on GitHub with references to commits that are related to them.

Commit should always be atomic. Keep solutions isolated whenever possible. Filler commits such as "clean up white space" or "fix typo" should be rebased out before making a pull request. Please ensure your commit history is clean and meaningful!

Code Formatting and Style
~~~~~~~~~~~~~~~~~~~~~~~~~
AIT makes a best-effort attempt at sticking with PEP-8 conventions. This is enforced automatically by ``black`` and checked by ``flake8``. You should run the ``pre-commit`` linting pipeline on any changes you make.

Testing
~~~~~~~
We do our best to make sure that all of our changes are tested. If you're fixing a bug you should always have an accompanying unit test to ensure we don't regress!

Check the Developer Tips section below for information on running each repository's test suite.

Pull Requests and Feature Branches
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
All changes should be isolated to a feature branch that links to a ticket. The standard across AIT projects is to use issue-### for branch names where ### is the issue number found on GitHub.

The title of a pull request should include a reference to the ticket being fixed as mentioned for commit messages. The description of a pull request should provide an in-depth explanation of the changes present. Note, if you wrote good commit messages this step should be easy!

Any tickets that are resolved by the pull request should be referenced with GitHub's syntax for closing out tickets. Assuming the above ticket we would have the following in a pull request description:

Changes are required to be reviewed by at least one member of the AIT PMC/Committers groups, tests must pass, and the branch must be up to date with master before changes will be merged. If changes are made as part of code review please ensure your commit history is cleaned up.

Resolve #248
--------------
