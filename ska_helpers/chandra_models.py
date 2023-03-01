# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Get data from chandra_models repository.
"""
import contextlib
import tempfile
import warnings
from pathlib import Path
from typing import Callable, Optional, Union

import git
import requests

from ska_helpers.paths import chandra_models_repo_path

__all__ = [
    "get_data",
    "get_repo_version",
    "get_github_version",
]

CHANDRA_MODELS_LATEST_URL = (
    "https://api.github.com/repos/sot/chandra_models/releases/latest"
)


def get_data(
    file_path: str | Path,
    version: Optional[str] = None,
    repo_path: Optional[str | Path] = None,
    require_latest_version: bool = False,
    timeout: int | float = 5,
    read_func: Optional[Callable] = None,
    read_func_kwargs: Optional[dict] = None,
) -> tuple:
    """
    Get data from chandra_models repository.

    Examples
    --------
    First we read the model specification for the ACA model. The ``get_data()`` function
    returns the text of the model spec so we need to use ``json.loads()`` to convert it
    to a dict.

        >>> import json
        >>> from astropy.io import fits
        >>> from ska_helpers import chandra_models

        >>> txt = chandra_models.get_data("chandra_models/xija/aca/aca_spec.json")
        >>> model_spec = json.loads(txt)
        >>> model_spec["name"]
        'aacccdpt'

    Next we read the acquisition probability model image. Since the image is a gzipped
    FITS file we need to use a helper function to read it.

        >>> def read_fits_image(file_path):
        ...     with fits.open(file_path) as hdus:
        ...         out = hdus[1].data
        ...     return out
        ...
        >>> acq_model_image = chandra_models.get_data(
        ...     "chandra_models/aca_acq_prob/grid-floor-2018-11.fits.gz",
        ...     read_func=read_fits_image
        ... )
        >>> acq_model_image.shape
        ...
        (141, 31, 7)

    Now let's get the version of the chandra_models repository::

        >>> chandra_models.get_repo_version()
        '3.47'


    Finally get version 3.30 of the ACA model spec from GitHub. The use of a lambda
    function to read the JSON file is compact but not recommended for production code.

        >>> model_spec_3_30 = chandra_models.get_data(
        ...     "chandra_models/xija/aca/aca_spec.json",
        ...     version="3.30",
        ...     repo_path="https://github.com/sot/chandra_models.git",
        ...     read_func=lambda fn: json.load(open(fn, "rb")),
        ... )
        >>> model_spec_3_30 == model_spec
        False

    Parameters
    ----------
    file_path : str, Path
        Name of model
    version : str
        Tag, branch or commit of chandra_models to use (default=latest tag from repo)
    repo_path : str, Path
        Path to directory or URL containing chandra_models repository (default is
        $SKA/data/chandra_models or the THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW
        environment variable if set)
    require_latest_version : bool
        Require that ``version`` matches the latest release on GitHub
    timeout : int, float
        Timeout (sec) for querying GitHub for the expected chandra_models version.
        Default = 5 sec.
    read_func : callable
        Optional function to read the data file. This function must take the file path
        as its first argument. If not provided then read the file as a text file.
    read_func_kwargs : dict
        Optional dict of kwargs to pass to ``read_func``.

    Returns
    -------
    tuple of dict, str
        Xija model specification dict, chandra_models version
    """
    if repo_path is None:
        repo_path = chandra_models_repo_path()

    # NOTE code in xija.get_model_spec.get_repo_version() that does something Windows
    # specific which I don't completely understand.
    #
    # with temp_directory() as repo_path_local:
    #     if platform.system() == 'Windows':
    #         repo = git.Repo.clone_from(repo_path, repo_path_local)
    #     else:
    #         repo = git.Repo(repo_path)

    # Potentially work in a clone of the repo in a temporary directory, but only if
    # necessary.
    with contextlib.ExitStack() as stack:
        if str(repo_path).startswith("https://github.com") or version is not None:
            # For a remote GitHub repo or non-default version, clone to a temp dir
            repo_path_local = stack.enter_context(tempfile.TemporaryDirectory())
            repo = git.Repo.clone_from(repo_path, repo_path_local)
            if version is not None:
                repo.git.checkout(version)
        else:
            # For a local repo at the default version use the existing directory
            repo = git.Repo(repo_path)
            repo_path_local = repo_path

        repo_file_path = Path(repo_path_local) / file_path
        if not repo_file_path.exists():
            raise FileNotFoundError(f"chandra_models {file_path=} does not exist")

        if version is None:
            # This also ensures that the repo is not dirty.
            version = get_repo_version(repo=repo)

        if require_latest_version:
            assert_latest_version(version, timeout)

        if read_func is None:
            data = repo_file_path.read_text()
        else:
            if read_func_kwargs is None:
                read_func_kwargs = {}
            data = read_func(repo_file_path, **read_func_kwargs)

    return data


def assert_latest_version(version, timeout):
    gh_version = get_github_version(timeout=timeout)
    if gh_version is None:
        warnings.warn(
            "Could not verify GitHub chandra_models release tag "
            f"due to timeout ({timeout} sec)"
        )
    elif version != gh_version:
        raise ValueError(
            f"version mismatch: local repo {version} vs " f"github {gh_version}"
        )


def get_repo_version(
    repo_path: Optional[Path] = None, repo: Optional[git.Repo] = None
) -> str:
    """Return version (most recent tag) of models repository.

    Returns
    -------
    str
        Version (most recent tag) of models repository
    """
    if repo is None:
        if repo_path is None:
            repo_path = chandra_models_repo_path()
        repo = git.Repo(repo_path)

    if repo.is_dirty():
        raise ValueError("repo is dirty")

    tags = sorted(repo.tags, key=lambda tag: tag.commit.committed_datetime)
    tag_repo = tags[-1]
    if tag_repo.commit != repo.head.commit:
        raise ValueError(f"repo tip is not at tag {tag_repo}")

    return tag_repo.name


def get_github_version(
    url: str = CHANDRA_MODELS_LATEST_URL, timeout: Union[int, float] = 5
) -> Optional[bool]:
    """Get latest chandra_models GitHub repo release tag (version).

    This queries GitHub for the latest release of chandra_models.

    Parameters
    ----------
    url : str
        URL for latest chandra_models release on GitHub API
    timeout : int, float
        Request timeout (sec, default=5)

    Returns
    -------
    str, None
        Tag name (str) of latest chandra_models release on GitHub.
        None if the request timed out, indicating indeterminate answer.
    """
    try:
        req = requests.get(url, timeout=timeout)
    except (requests.ConnectTimeout, requests.ReadTimeout):
        return None

    if req.status_code != requests.codes.ok:
        req.raise_for_status()

    page_json = req.json()
    return page_json["tag_name"]
