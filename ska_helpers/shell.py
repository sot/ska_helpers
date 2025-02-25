# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Utilities to run subprocesses"""

import functools
import re
import os
import subprocess


__all__ = [
    "ShellError",
    "getenv",
    "importenv",
]


class ShellError(Exception):
    pass


def _fix_paths(
    envs,
    pathvars=(
        "PATH",
        "PERLLIB",
        "PERL5LIB",
        "PYTHONPATH",
        "LD_LIBRARY_PATH",
        "MANPATH",
        "INFOPATH",
    ),
):
    """For the specified env vars that represent a search path, make sure that the
    paths are unique.  This allows the environment setting script to be lazy
    and not worry about it.  This routine gives the right-most path precedence
    and modifies C{envs} in place.

    :param envs: Dict of environment vars
    :param pathvars: List of path vars that will be fixed
    :rtype: None (envs is modified in-place)
    """

    # Process env vars that are contained in the PATH_ENVS set
    for key in set(envs.keys()) & set(pathvars):
        path_ins = envs[key].split(":")
        pathset = set()
        path_outs = []
        # Working from right to left add each path that hasn't been included yet.
        for path in reversed(path_ins):
            if path not in pathset:
                pathset.add(path)
                path_outs.append(path)
        envs[key] = ":".join(reversed(path_outs))


def _parse_keyvals(keyvals):
    """Parse the key=val pairs from the newline-separated string.

    :param keyvals: Newline-separated string with key=val pairs
    :rtype: Dict of key=val pairs.
    """
    print("KEYVALS", keyvals)
    re_keyval = re.compile(r"([\w_]+) \s* = \s* (.*)", re.VERBOSE)
    keyvalout = {}
    for keyval in keyvals:
        m = re.match(re_keyval, keyval)
        if m:
            key, val = m.groups()
            keyvalout[key] = val
    return keyvalout


@functools.cache
def _shell_ok(shell):
    p = subprocess.run(
        ["which", shell], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    return p.returncode == 0


def getenv(cmdstr, shell="bash", env=None, clean=True):
    """
    Run the command string ``cmdstr`` in a ``shell`` ('bash' or 'tcsh').  It can have
    multiple lines.  Each line is separately sent to the shell.  The exit status is
    checked if the shell comes back with a prompt. If exit status is non-zero at any point
    then processing is terminated and a ``ShellError`` exception is raise.

    :param cmdstr: command string
    :param shell: shell for command -- 'bash' (default) or 'tcsh'
    :param env: set environment using ``env`` dict prior to running commands
    :param clean: if True, do not inherit the current environment (default)

    :rtype: (outlines, deltaenv)
    """
    environ = {} if clean else dict(os.environ)
    if env is not None:
        environ.update(env)

    if not _shell_ok(shell):
        raise Exception(f'Failed to find "{shell}" shell')

    if getenv:
        cmdstr += " && echo __PRINTENV__ && printenv"

    # all lines are joined so the shell exits at the first failure
    cmdstr = " && ".join([c for c in cmdstr.splitlines() if c.strip()])

    # make sure the RC file is not sourced
    if shell in ["tcsh", "csh"]:
        cmdstr = f"{shell} -f -c '{cmdstr}'"
        shell = "bash"

    proc = subprocess.run(
        [cmdstr],
        executable=shell,
        shell=True,
        env=environ,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout = proc.stdout.decode().strip()

    if proc.returncode:
        msg = " ".join(stdout[-1:])  # stdout could be empty
        exc = ShellError(f"Shell error: {msg}")
        exc.lines = stdout
        raise exc

    newenv = {}
    if "__PRINTENV__" in stdout:
        newenv = _parse_keyvals(stdout[stdout.index("__PRINTENV__") + 1 :].splitlines())
        stdout = stdout[: stdout.index("__PRINTENV__")]

    return newenv


def importenv(cmdstr, shell="bash", env=None, clean=True):
    """Run ``cmdstr`` in a bash shell and import the environment updates into the
    current python environment (os.environ).  See ``bash_shell`` for options.

    :returns: Dict of environment vars update produced by ``cmdstr``
    """
    newenv = getenv(cmdstr, env=env, shell=shell, clean=clean)

    # Update os.environ based on changes to environment made by cmdstr
    deltaenv = {}
    if importenv or getenv:
        expected_diff_set = (
            {"PS1", "PS2", "_", "SHLVL"} if shell in ["bash", "zsh"] else set()
        )
        currenv = dict(os.environ)
        _fix_paths(newenv)
        for key in set(newenv) - expected_diff_set:
            if key not in currenv or currenv[key] != newenv[key]:
                deltaenv[key] = newenv[key]
        if importenv:
            os.environ.update(deltaenv)
    return newenv
