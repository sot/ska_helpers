import pytest
import tempfile
from ska_helpers import git_helpers
import git
import os

from testr.test_helper import on_head_network

# @pytest.mark.filterwarnings("ignore:Updating git config")
@pytest.mark.skipif(not on_head_network(), reason='bla')
def test_make_git_repo_safe():
    with tempfile.TemporaryDirectory() as d, pytest.warns(
        UserWarning, match="Updating git config"
    ):
        os.environ["HOME"] = d
        repo = git.Repo("/proj/sot/ska/data/chandra_models")
        with pytest.raises(git.exc.GitCommandError):
            repo.is_dirty()
        git_helpers.make_git_repo_safe("/proj/sot/ska/data/chandra_models")
        repo.is_dirty()
