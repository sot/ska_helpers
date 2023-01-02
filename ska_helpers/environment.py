# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
The ``ska_helpers.environment`` module provides a function to configure the Ska3
runtime environment at the point of import of every Ska3 package.
"""

import os


def configure_ska_environment():
    """Configure environment for Ska3 runtime.

    This is called by ska_helpers.version.get_version() and thus gets called
    upon import of every Ska3 package.

    This includes setting NUMBA_CACHE_DIR to $HOME/.ska3/cache/numba if that env
    var is not already defined.  This is to avoid problems with read-only
    filesystems.
    """
    # If not already defined, set NUMBA_CACHE_DIR to a writable directory in the
    # user's home directory $HOME/.ska3/cache/numba. The numba default is to put
    # files into the package distribution directory, which is read-only on Ska3
    # on HEAD and GRETA. Note that numba will create this directory if it does exist,
    # potentially including subdirectories.
    numba_cache_dir = os.path.join(os.path.expanduser("~"), ".ska3", "cache", "numba")
    os.environ.setdefault("NUMBA_CACHE_DIR", numba_cache_dir)
