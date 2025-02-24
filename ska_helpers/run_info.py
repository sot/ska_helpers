# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
The ``ska_helpers.run_info`` module provides convenience functions to get
and print relevant run time information such as machine name, user name, date,
program version, and so on.  This is aimed at executable scripts and cron jobs.
"""

import inspect
import os
import platform
import pprint
import time

from ska_helpers import __version__  # noqa

__all__ = ["get_run_info", "get_run_info_lines", "log_run_info", "__version__"]


def get_run_info(opt=None, *, version=None, stack_level=1):
    """Get run time information as dict.

    Parameters
    ----------
    opt :
        argparse options (Default value = None)
    version :
        program version (default=__version__ in calling module)
    stack_level :
        stack level for getting calling module (Default value = 1)

    Returns
    -------
    dcit
        run information

    """
    calling_frame_record = inspect.stack()[stack_level]
    calling_func_file = calling_frame_record[1]

    if version is None:
        calling_frame = calling_frame_record[0]
        version = calling_frame.f_globals.get("__version__", "undefined")

    info = {
        "filename": calling_func_file,
        "version": version,
        "time": time.ctime(),
        "user": os.getlogin(),
        "machine": platform.node(),
        "args": vars(opt) if hasattr(opt, "__dict__") else opt,
    }
    return info


def get_run_info_lines(opt=None, *, version=None, stack_level=2):
    """Get run time information as formatted lines.

    Parameters
    ----------
    opt :
        argparse options (Default value = None)
    version :
        program version (default=__version__ in calling module)
    stack_level :
        stack level for getting calling module (Default value = 2)

    Returns
    -------
    list
        formatted information lines

    """
    info = get_run_info(opt, version=version, stack_level=stack_level)
    info_lines = [
        f"******************************************",
        f"Running: {info['filename']}",
        f"Version: {info['version']}",
        f"Time: {info['time']}",
        f"User: {info['user']}",
        f"Machine: {info['machine']}",
        f"Processing args:",
    ]
    info_lines.extend(pprint.pformat(info["args"]).splitlines())
    info_lines.append("******************************************")

    return info_lines


def log_run_info(log_func, opt=None, *, version=None, stack_level=3):
    """Output run time information as formatted lines via ``log_func``.

    Each formatted line is passed to ``log_func``.

    Parameters
    ----------
    log_func :
        logger output function (e.g. logger.info)
    opt :
        argparse options (Default value = None)
    version :
        program version (default=__version__ in calling module)
    stack_level :
        stack level for getting calling module (Default value = 3)
    """
    info_lines = get_run_info_lines(opt, version=version, stack_level=stack_level)
    for line in info_lines:
        log_func(line)
