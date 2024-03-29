# Licensed under a 3-clause BSD style license - see LICENSE.rst
import getpass
import tempfile
from packaging.version import Version

import git
import pytest

from ska_helpers import git_helpers, paths
from ska_helpers.utils import get_owner

CHANDRA_MODELS = paths.chandra_models_repo_path()


def ska_ownership_ok():
    # Check that the OS and volume support file ownership
    # (not the case with shared directories on a Windows VM on parallels)
    # and that the chandra_models dir is owned by the current user
    try:
        return get_owner(CHANDRA_MODELS) == getpass.getuser()
    except Exception:
        return False


def git_version_old():
    # Is the git version too old to have the repo_safe feature?
    # The safe checking feature was added in git 2.35.2.
    # This Git().version_info is the version of git not gitpython.
    git_version = ".".join(str(val) for val in git.Git().version_info)
    return Version(git_version) < Version("2.35.2")


@pytest.mark.skipif(
    not CHANDRA_MODELS.exists(),
    reason="Chandra models dir is not there",
)
@pytest.mark.skipif(ska_ownership_ok(), reason="Chandra models dir ownership is OK")
@pytest.mark.skipif(git_version_old(), reason="Git version is too old to care")
def test_make_git_repo_safe(monkeypatch):
    # Clear the 'repo_safe' cache so that this test always has something to do.
    git_helpers.make_git_repo_safe.cache_clear()

    with tempfile.TemporaryDirectory() as tempdir:
        # temporarily set HOME to a temp dir so .gitconfig comes from there
        monkeypatch.setenv("HOME", tempdir)
        repo = git.Repo(CHANDRA_MODELS)
        with pytest.raises(git.exc.GitCommandError):
            # This statement fails with the error
            #     fatal: detected dubious ownership
            # unless the repo is marked safe in .gitconfig
            repo.is_dirty()
        with pytest.warns(UserWarning, match="Updating git config"):
            # marke the repo safe and issue warning
            git_helpers.make_git_repo_safe(CHANDRA_MODELS)
        # success
        repo.is_dirty()
