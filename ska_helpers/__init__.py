"""
Ska_helpers is a collection of utilities for the Ska3 runtime environment.

ska_helpers.version
-------------------
- get_version: get the version from installed package information or git.
- parse_version: parse the version into a dict of components.
"""
from .version import get_version

__version__ = get_version(__package__)
