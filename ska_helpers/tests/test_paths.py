# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
from pathlib import Path

import pytest

from ska_helpers import paths

SOME_ENV_VAR_DEFINED = any(
    os.environ.get(nm) for nm in paths.CHANDRA_MODELS_ROOT_ENV_VARS
)


@pytest.mark.skipif(SOME_ENV_VAR_DEFINED, reason="Test requires clean environment")
@pytest.mark.parametrize("repo_source", ["default", "env", "kwargs"])
@pytest.mark.parametrize("chandra_models_repo_dir", paths.CHANDRA_MODELS_ROOT_ENV_VARS)
def test_chandra_models_paths(repo_source, chandra_models_repo_dir, monkeypatch):
    if repo_source == "env":
        root = Path("/", "foo", "chandra_models")
        monkeypatch.setenv(chandra_models_repo_dir, str(root))
        kwargs = {}
    elif repo_source == "default":
        # Make sure no path-changing env vars are set
        for env_var in paths.CHANDRA_MODELS_ROOT_ENV_VARS:
            monkeypatch.delenv(env_var, raising=False)
        root = Path(os.environ["SKA"]) / "data" / "chandra_models"
        kwargs = {}
    elif repo_source == "kwargs":
        root = Path("/", "bar", "chandra_models")
        kwargs = {"repo_path": str(root)}
    else:
        raise ValueError(f"Unexpected repo_source={repo_source}")

    if repo_source == "kwargs":
        repo = Path(root)
    else:
        repo = paths.chandra_models_repo_path()
    assert repo == root

    mdls = paths.chandra_models_path(**kwargs)
    assert mdls == root / "chandra_models"

    drift = paths.aca_drift_model_path(**kwargs)
    assert drift == mdls / "aca_drift" / "aca_drift_model.json"

    acq_prob = paths.aca_acq_prob_models_path(**kwargs)
    assert acq_prob == mdls / "aca_acq_prob"

    xija = paths.xija_models_path(**kwargs)
    assert xija == mdls / "xija"
