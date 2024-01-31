# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
The ``ska_helpers.version`` module provides utilities to handle package
versions. The version of a package is determined using importlib if it is
installed, and `setuptools_scm <https://github.com/pypa/setuptools_scm/>`_
otherwise.
"""

import importlib
import io
import logging
import os
import re
import warnings
from pathlib import Path

from ska_helpers.logging import basic_logger

from .environment import configure_ska_environment

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", message=r"Module \w+ was already imported", category=UserWarning
    )
    from importlib import resources, metadata


def get_version_logger(level_stdout, level_string):
    logger_string = io.StringIO()
    hdlr_stdout = logging.StreamHandler()
    hdlr_stdout.setLevel(level_stdout)
    hdlr_string = logging.StreamHandler(logger_string)
    hdlr_string.setLevel(level_string)

    logger = basic_logger(
        __name__,
        level="DEBUG",
        format="%(message)s",
        handlers=[hdlr_stdout, hdlr_string],
        force=True,
    )
    return logger, logger_string


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

    # Configure environment for Ska3 runtime. This is a bit of a hack but get_version()
    # is a convenient place to do this because it is called by every Ska3 package
    # on import.
    configure_ska_environment()

    level_stdout = "DEBUG" if "SKA_HELPERS_VERSION_DEBUG" in os.environ else "INFO"
    level_string = "DEBUG"
    logger, logger_string = get_version_logger(level_stdout, level_string)
    log = logger.debug

    log("*" * 80)
    log(f"Getting version for package={package} distribution={distribution} ")
    log(f"  Current directory: {Path.cwd()}")
    log(f"  {sys.path=}")

    # Get module file for package.
    module_file = importlib.util.find_spec(package, distribution).origin
    log(f"  {module_file=}")

    # From this point guarantee tha a version string is returned.
    try:
        try:
            # Get a distribution, which may or may not correspond to the package
            # # that gets imported (we check that next).  For some packages, e.g.
            # cheta or pyyaml, the distribution will be different from the
            # package.
            log(
                "  Getting distribution "
                f"dist_info=get_distribution({distribution or package})"
            )
            version = metadata.version(distribution or package)
            location = resources.files(distribution or package)
            log(f"    {location=}")
            log(f"    {version=}")

            # If the dist_info.location appears to be a git repo, then
            # importlib has gotten a "local" distribution and the
            # version just corresponds to whatever version was the
            # last run of "setup.py sdist" or "setup.py bdist_wheel", i.e.
            # unrelated to current version, so ignore in this case.
            git_dir = location.parent / ".git"
            bad = git_dir.exists() and git_dir.is_dir()
            if bad:
                log(
                    "    WARNING: distinfo.location is git repo (version likely wrong), "
                    "falling through to setuptools_scm"
                )
            else:
                log("    distinfo.location looks OK (not a git repo)")
            assert not bad

        except (metadata.PackageNotFoundError, AssertionError):
            # metadata.version failed or found a different package from this
            # file, try getting version from source repo.
            from setuptools_scm import get_version

            log("  Getting version via setuptools_scm for git repo")

            # Define root as N directories up from location of __init__.py based
            # on package name.
            roots = [".."] * len(package.split("."))
            if os.path.basename(module_file) != "__init__.py":
                roots = roots[:-1]
            log(f"    Running get_version(")
            log(f"        root={Path(*roots)},")
            log(f"        relative_to={module_file}")
            log(f"    )")
            version = get_version(root=Path(*roots), relative_to=module_file)

    except Exception:
        # Something went wrong. The ``get_version` function should never block
        # import but generate a lot of output indicating the problem.
        import traceback
        import warnings

        version = "0.0.0"
        log(f"WARNING: got {version=}")
        log("*" * 80)

        if "TESTR_FILE" not in os.environ:
            # this avoids a test failure when checking log files with this warning.
            # Pytest will import packages such as Ska.Shell first as Shell and then as Ska.Shell.
            # https://docs.pytest.org/en/latest/pythonpath.html

            # Monkeypatch to not show the source line along with the warning. See
            # https://stackoverflow.com/questions/2187269.
            def custom_formatwarning(msg, *args, **kwargs):
                # ignore everything except the message
                return str(msg) + "\n"

            warnings.formatwarning = custom_formatwarning

            warnings.warn(traceback.format_exc() + "\n\n")
            warnings.warn("Failed to find a package version, setting to 0.0.0")
            warnings.warn(logger_string.getvalue())

    else:
        # No exception, so we got a valid version string.
        log(f"SUCCESS: got {version=}")
        log("*" * 80)

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
