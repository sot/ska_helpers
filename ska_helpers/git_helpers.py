# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Helper functions for using git.
"""
import functools
import re
import subprocess
import sys
import warnings
from pathlib import Path

from ska_file import chdir


__all__ = ["make_git_repo_safe"]


@functools.lru_cache()
def make_git_repo_safe(path: str | Path) -> None:
    """Ensure git repo at ``path`` is a safe git repository.

    A "safe" repo is one which is owned by the user calling this function. See:
    https://github.blog/2022-04-12-git-security-vulnerability-announced/#cve-2022-24765

    If an unsafe repo is detected then this command issues a warning to that
    effect and then updates the user's git config to add this repo as a safe
    directory.

    This function should only be called for known safe git repos such as
    ``$SKA/data/chandra_models``.

    :param path: str, Path
        Path to top level of a git repository
    """  # noqa
    path = Path(path)
    if not (path / ".git").exists():
        raise FileNotFoundError(f"'{path}' is not the top level of a git repo")

    with chdir(path):
        # Run a lightweight command which will fail for an unsafe repo
        proc = subprocess.run(["git", "rev-parse"], capture_output=True)
        if proc.returncode != 0:
            _handle_rev_parse_failure(path, proc)
            # Ensure that the repo is now safe. This will raise an exception
            # otherwise.
            subprocess.check_call(["git", "rev-parse"])


def _handle_rev_parse_failure(path: Path, proc: subprocess.CompletedProcess):
    """Handle a failure of `git --rev-parse` command.

    This is most likely due to repo not being safe. If that is the case (based
    on the command error output) then issue a warning and update the user git
    config. Otherwise print the error text and raise an exception.
    """
    # Regex of command that is provided by git to mark a directory as safe. The
    # suggested directory name (last group) may be very different from the
    # original ``path``. For example on Windows with a VM shared directory
    # Y:\data\chandra_models, the required git config safe.directory is
    # %(prefix)///Mac/ska/data/chandra_models. Using the original ``path`` does
    # not work.
    git_safe_config_RE = (
        r"(git) (config) (--global) (--add) (safe\.directory) (\S+)"
    )

    # Error message from the failed git command, which looks like this:
    # $ git status
    # fatal: detected dubious ownership in repository at '//Mac/Home/ska/data/chandra_models'  # noqa: E501
    # To add an exception for this directory, call:
    #
    #    git config --global --add safe.directory '%(prefix)///Mac/Home/ska/data/chandra_models'  # noqa: E501

    err = proc.stderr.decode().strip()

    if match := re.search(git_safe_config_RE, err, re.MULTILINE):
        cmds = list(match.groups())
        cmds[-1] = cmds[-1].strip("'")
        warnings.warn(
            "Updating git config to allow read-only git operations on "
            f"trusted repository {path}. Contact Ska team for questions.",
            stacklevel=3,
        )
        subprocess.check_call(cmds)
    else:
        print(err, file=sys.stderr)
        proc.check_returncode()
