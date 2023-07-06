import pytest
import tempfile
from ska_helpers import git_helpers
import git
import os
from pathlib import Path


CHANDRA_MODELS = Path(os.environ["SKA"]) / "data" / "chandra_models"


def ska_ownership_ok():
    try:
        return CHANDRA_MODELS.owner() == os.getlogin()
    except Exception:
        return False


@pytest.mark.skipif(
    not CHANDRA_MODELS.exists(), reason="Chandra models dir is not there"
)
@pytest.mark.skipif(ska_ownership_ok(), reason="Chandra models dir ownership is OK")
def test_make_git_repo_safe(monkeypatch):
    with (
        tempfile.TemporaryDirectory() as tempdir,
        pytest.warns(UserWarning, match="Updating git config"),
    ):
        monkeypatch.setenv("HOME", tempdir)
        repo = git.Repo(CHANDRA_MODELS)
        with pytest.raises(git.exc.GitCommandError):
            repo.is_dirty()
        git_helpers.make_git_repo_safe(CHANDRA_MODELS)
        repo.is_dirty()
