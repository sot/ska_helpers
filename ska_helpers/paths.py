# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
from pathlib import Path

# Name of environment variable to override default root for chandra_models repository
# directory. The name is misleading but this is used by the Matlab tools to override the
# default root for chandra_models.
CHANDRA_MODELS_ROOT_ENV_VAR = "THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW"


def chandra_models_repo_path() -> Path:
    """Get path to chandra_models git repository.

    This returns a Path object pointing at the ``chandra_models`` repository in the
    Ska data directory. By default is this returns ``$SKA/data/chandra_models``.

    If the environment variable ``THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW`` is set then
    the path will be ``$THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW``.

    :returns: Path object
        Path to ``chandra_models`` repository
    """
    default_root = Path(
        os.environ["SKA"],
        "data",
        "chandra_models",
    )
    root = os.environ.get(CHANDRA_MODELS_ROOT_ENV_VAR, default_root)

    return Path(root)


def chandra_models_path(repo_path=None) -> Path:
    """Get path to chandra_models data files directory.

    This returns a Path object pointing at the ``chandra_models/`` directory in the
    ``chandra_models`` repository.

    :param repo_path: optional
        Path to chandra_models repository (default described above)
    :returns: Path object
        Path to ``chandra_models`` data files directory.
    """
    if repo_path is None:
        repo_path = chandra_models_repo_path()
    else:
        repo_path = Path(repo_path)

    path = repo_path / "chandra_models"

    return path


def aca_drift_model_path(repo_path=None) -> Path:
    """
    Get path to chandra_models aca_drift_model.json file.

    :param repo_path: optional
        Path to chandra_models repository
    :returns: Path object
        Path to chandra_models ``aca_drift_model.json`` file.
    """
    path = chandra_models_path(repo_path) / "aca_drift" / "aca_drift_model.json"

    return path


def aca_acq_prob_models_path(repo_path=None) -> Path:
    """
    Get path to chandra_models aca_acq_prob models directory.

    :param repo_path: optional
        Path to chandra_models repository
    :returns: Path object
        Path to chandra_models ``aca_acq_prob`` models directory.
    """
    path = chandra_models_path(repo_path) / "aca_acq_prob"

    return path


def xija_models_path(repo_path=None) -> Path:
    """
    Get path to chandra_models xija models directory.

    :param repo_path: optional
        Path to chandra_models repository
    :returns: Path object
        Path to chandra_models ``xija`` models directory.
    """
    path = chandra_models_path(repo_path) / "xija"

    return path
