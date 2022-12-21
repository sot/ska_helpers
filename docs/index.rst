.. ska_helpers documentation master file, created by
   sphinx-quickstart on Fri Dec 13 09:48:53 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Ska Package Helpers
===================

.. automodule:: ska_helpers
   :members:

Logging
-------

.. automodule:: ska_helpers.logging
   :members:


Retry
-----

.. automodule:: ska_helpers.retry
   :members:


Setup Helpers
-------------

.. automodule:: ska_helpers.setup_helper
   :members:


Utilities
---------

.. automodule:: ska_helpers.utils
   :members:


Get Version
-----------

.. automodule:: ska_helpers.version
   :members:


Default versioning scheme
^^^^^^^^^^^^^^^^^^^^^^^^^^

What follows is the scheme as described in `setuptools_scm's documentation
<https://github.com/pypa/setuptools_scm/>`_.

In the standard configuration ``setuptools_scm`` takes a look at three things:

1. latest tag (with a version number)
2. the distance to this tag (e.g. number of revisions since latest tag)
3. workdir state (e.g. uncommitted changes since latest tag)

and uses roughly the following logic to render the version:

no distance and clean:
    ``{tag}``
distance and clean:
    ``{next_version}.dev{distance}+{scm letter}{revision hash}``
no distance and not clean:
    ``{tag}+dYYYMMMDD``
distance and not clean:
    ``{next_version}.dev{distance}+{scm letter}{revision hash}.dYYYMMMDD``

The next version is calculated by adding ``1`` to the last numeric component of
the tag.

For Git projects, the version relies on `git describe <https://git-scm.com/docs/git-describe>`_,
so you will see an additional ``g`` prepended to the ``{revision hash}``.


Due to the default behavior it's necessary to always include a
patch version (the ``3`` in ``1.2.3``), or else the automatic guessing
will increment the wrong part of the SemVer (e.g. tag ``2.0`` results in
``2.1.devX`` instead of ``2.0.1.devX``). So please make sure to tag
accordingly.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Run time information
--------------------

.. automodule:: ska_helpers.run_info
   :members:




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
