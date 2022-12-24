# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
The ``ska_helpers.version`` module provides utilities to handle package
versions. The version of a package is determined using pkg_resources if it is
installed, and `setuptools_scm <https://github.com/pypa/setuptools_scm/>`_
otherwise.
"""

import importlib
import os
import re
import warnings
from pathlib import Path

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", message=r"Module \w+ was already imported", category=UserWarning
    )
    from pkg_resources import DistributionNotFound, get_distribution


def get_version(package, distribution=None):
    """Get version string for ``package`` with optional ``distribution`` name.

    If the package is not from an installed distribution then get version from
    git using setuptools_scm.

    Parameters
    ----------
    package :
        package name, typically __package__
    distribution :
        name of distribution if different from ``package`` (Default value = None)

    Returns
    -------
    str
        Version string

    """
    import sys

    debug = "SKA_HELPERS_VERSION_DEBUG" in os.environ
    if debug:
        print("*" * 80)
        print(f"Getting version for package={package} distribution={distribution} ")
        print(f"  Current directory: {Path.cwd()}")
        print(f"  {sys.path=}")

    # Get module file for package.
    module_file = importlib.util.find_spec(package, distribution).origin
    if debug:
        print(f"  {module_file=}")

    # From this point guarantee tha a version string is returned.
    try:
        try:
            # Get a distribution, which may or may not correspond to the package
            # # that gets imported (we check that next).  For some packages, e.g.
            # cheta or pyyaml, the distribution will be different from the
            # package.
            if debug:
                print(
                    "  Getting distribution "
                    f"dist_info=get_distribution({distribution or package})"
                )
            dist_info = get_distribution(distribution or package)
            version = dist_info.version
            if debug:
                print(f"    {dist_info.location=}")
                print(f"    {dist_info.version=}")

            # Check if the imported package __init__.py file has the same location
            # as the distribution that was found.  If working in a local git repo
            # that does not have a <package>.egg-info directory, get_distribution()
            # will find an installed version.  Windows does not necessarily
            # respect the case so downcase everything.
            ok = module_file.lower().startswith(dist_info.location.lower())
            if debug:
                if ok:
                    print("    distinfo.location matches module_file")
                else:
                    print(
                        "    FAIL: distinfo.location does not match module_file, "
                        "falling through to setuptools_scm"
                    )
            assert ok

            # If the dist_info.location appears to be a git repo, then
            # get_distribution() has gotten a "local" distribution and the
            # dist_info.version just corresponds to whatever version was the
            # last run of "setup.py sdist" or "setup.py bdist_wheel", i.e.
            # unrelated to current version, so ignore in this case.
            git_dir = Path(dist_info.location, ".git")
            bad = git_dir.exists() and git_dir.is_dir()
            if debug:
                if bad:
                    print(
                        "    FAIL: distinfo.location is git repo (version likely wrong), "
                        "falling through to setuptools_scm"
                    )
                else:
                    print("    distinfo.location looks OK (not a git repo)")
            assert not bad

        except (DistributionNotFound, AssertionError):
            # Get_distribution failed or found a different package from this
            # file, try getting version from source repo.
            from setuptools_scm import get_version

            if debug:
                print("  Getting version via setuptools_scm for git repo")

            # Define root as N directories up from location of __init__.py based
            # on package name.
            roots = [".."] * len(package.split("."))
            if os.path.basename(module_file) != "__init__.py":
                roots = roots[:-1]
            if debug:
                print(f"    Running get_version(")
                print(f"        root={Path(*roots)},")
                print(f"        relative_to={module_file}")
                print(f"    )")
            version = get_version(root=Path(*roots), relative_to=module_file)

    except Exception:
        # Something went wrong. The ``get_version` function should never block
        # import but generate a lot of output indicating the problem.
        import traceback
        import warnings

        if "TESTR_FILE" not in os.environ:
            # this avoids a test failure when checking log files with this warning.
            # Pytest will import packages such as Ska.Shell first as Shell and then as Ska.Shell.
            # https://docs.pytest.org/en/latest/pythonpath.html
            warnings.warn(traceback.format_exc() + "\n\n")
            warnings.warn("Failed to find a package version, setting to 0.0.0")

        version = "0.0.0"

        if debug:
            print(f"FAIL: got {version=}")

    else:
        # No exception, so we got a valid version string.
        if debug:
            print(f"SUCCESS: got {version=}")

    if debug:
        print("*" * 80)

    return version


def parse_version(version):
    """Parse version string and return a dictionary with version information.
    This only handles the default scheme.

    Parameters
    ----------
    version :
        str

    Returns
    -------
    dict
        version information

    """
    fmt = (
        r"(?P<major>[0-9]+)(.(?P<minor>[0-9]+))?(.(?P<patch>[0-9]+))?"
        r"(.dev(?P<distance>[0-9]+))?"
        r"(\+(?P<letter>\S)g?(?P<hash>\S+)\.(d(?P<date>[0-9]+))?)?"
    )
    m = re.match(fmt, version)
    if not m:
        raise RuntimeError(f"version {version} could not be parsed")
    result = m.groupdict()
    for k in ["major", "minor", "patch", "distance"]:
        result[k] = eval(f"{result[k]}")
    return result
