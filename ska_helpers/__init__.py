# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Ska_helpers is a collection of utilities for the Ska3 runtime environment.
"""

from .version import get_version

__version__ = get_version(__package__)


def test(*args, **kwargs):
    """
    Run py.test unit tests.
    """
    import testr

    return testr.test(*args, **kwargs)
