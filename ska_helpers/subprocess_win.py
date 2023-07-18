# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Fix subprocess high-level functions on Windows via MATLAB pyexec().

For the subprocess functions ``run``, ``call``, ``check_call``, and ``check_output``,
this module defines thin wrappers that change the following argument defaults to fix
issues on Windows:

- ``stdin`` is set to ``subprocess.DEVNULL`` if not specified.
- ``creationflags`` has the ``subprocess.CREATE_NO_WINDOW`` flag set.

On non-Windows platforms these wrappers are no-ops.

See also discussion in https://github.com/sot/ska_helpers/pull/42.

The ``stdin`` fix addresses this exception:
```
>> pyexec('proc = subprocess.run(["git", "rev-parse"], capture_output=True)')
  ...
PYPROC: Error executing python statement: 'proc = subprocess.run(["git", "rev-parse"],
        capture_output=True)' - [WinError 6] The handle is invalid
```

The ``creationflags`` fix addresses the problem of a console window popping up when
running a subprocess command within the MATLAB environment.
"""
import functools
import subprocess

from testr.test_helper import is_windows

__all__ = ["run", "call", "check_call", "check_output"]


def fix_windows_subprocess(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if is_windows():
            if "stdin" not in kwargs:
                kwargs["stdin"] = subprocess.DEVNULL

            if "creationflags" in kwargs:
                kwargs["creationflags"] |= subprocess.CREATE_NO_WINDOW
            else:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        return func(*args, **kwargs)

    return wrapper


# Fix subprocess high-level functions on Windows
run = fix_windows_subprocess(subprocess.run)
call = fix_windows_subprocess(subprocess.call)
check_call = fix_windows_subprocess(subprocess.check_call)
check_output = fix_windows_subprocess(subprocess.check_output)
