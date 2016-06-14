=========
gg-commit
=========

.. image:: https://travis-ci.org/peterbe/gg-commit.svg?branch=master
    :target: https://travis-ci.org/peterbe/gg-commit

.. image:: https://badge.fury.io/py/gg-commit.svg
    :target: https://pypi.python.org/pypi/gg-commit

A plugin for `gg <https://github.com/peterbe/gg>`_ for committing branches.


Installation
============

This is a plugin that depends on `gg <https://github.com/peterbe/gg>`_
which gets automatically
installed if it's not already available::

    pip install gg-commit

This plugin is ideally useful in conjunction with `gg-start
<https://github.com/peterbe/gg-start>`_ which helps you create new
branches.

How to develop
==============

To work on this, first run::

    pip install -U --editable .

That installs the package ``gg`` and its dependencies. It also
installs the executable ``gg``. So now you should be able to run::

    gg commit --help


Version History
===============

0.1
  * Proof of concept
