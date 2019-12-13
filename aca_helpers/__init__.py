"""
ACA Helpers is a collection of utilities for ACA packages.
It currently includes:

- get_version. A function to get the version from installed package information ot git.
"""
from .version import get_version

__version__ = get_version()
