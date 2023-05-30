# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
from pathlib import Path

# Name of environment variables that can be set to override default root for
# chandra_models repository directory. The second name is misleading but this is used by
# the Matlab tools to override the default root for chandra_models.
CHANDRA_MODELS_ROOT_ENV_VARS = [
    "CHANDRA_MODELS_REPO_DIR",
    "THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW",
]


def chandra_models_repo_path() -> Path:
    """Get path to chandra_models git repository.

    This returns a Path object pointing at the ``chandra_models`` repository in the
    Ska data directory. By default is this returns ``$SKA/data/chandra_models``.

    The default root can be overridden by setting either of these environment variables,
    which are checked in the order listed:

    - ``CHANDRA_MODELS_REPO_DIR``
    - ``THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW``

    :returns: Path object
        Path to ``chandra_models`` repository
    """
    for env_var in CHANDRA_MODELS_ROOT_ENV_VARS:
        if env_var in os.environ:
            return Path(os.environ[env_var])

    default_root = Path(
        os.environ["SKA"],
        "data",
        "chandra_models",
    )
    return default_root


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
