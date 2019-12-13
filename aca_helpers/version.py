"""
This module provides utilities to handle package versions. The version of a package is determined
using pkg_resources if it is installed, and
`setuptools_scm <https://github.com/pypa/setuptools_scm/>`_ otherwise.
"""

import re
import importlib
from pkg_resources import get_distribution, DistributionNotFound


def get_version(package=None):
    """
    Get version string. If there is no package info, get it from git.

    :return: str
        The version string
    """
    if not package:
        package = __package__

    errors = []
    try:
        dist_info = get_distribution(package)
        version = dist_info.version
    except DistributionNotFound:
        dist_info = None
        version = None
        errors.append(f'No pkg_resources found for {package}')

    # this appears to be cyclic, but it is not.
    # When called from within __init__.py, the module is not completely defined yet,
    # but that is not an issue here.
    module = importlib.import_module(package)
    if not version or not module.__file__.lower().startswith(dist_info.location.lower()):
        try:
            from setuptools_scm import get_version
            version = get_version(root='..', relative_to=module.__file__)
        except Exception as err:
            errors.append(err)

    if not version:
        error = f'Failed to find a package version for {package}'
        for err in errors:
            error += f'\n - Error: {err}'

    return version


def parse_version(version):
    """
    Parse version string and return a dictionary with version information.
    This only handles the default scheme.

    :param version: str
    :return: dict
    """
    fmt = '(?P<major>[0-9]+)(.(?P<minor>[0-9]+))?(.(?P<patch>[0-9]+))?' \
          '(.dev(?P<distance>[0-9]+))?'\
          '(\+(?P<letter>\S)g?(?P<hash>\S+)\.(d(?P<date>[0-9]+))?)?'
    m = re.match(fmt, version)
    if not m:
        raise RuntimeError(f'version {version} could not be parsed')
    result = m.groupdict()
    return result
