# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Get data from chandra_models repository.
"""
import contextlib
import functools
import hashlib
import os
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Callable, Optional, Union

import git
import requests

from ska_helpers.git_helpers import make_git_repo_safe
from ska_helpers.paths import chandra_models_repo_path
from ska_helpers.utils import LRUDict

__all__ = [
    "chandra_models_cache",
    "get_data",
    "get_repo_version",
    "get_github_version",
]

CHANDRA_MODELS_LATEST_URL = (
    "https://api.github.com/repos/sot/chandra_models/releases/latest"
)

ENV_VAR_NAMES = [
    "CHANDRA_MODELS_REPO_DIR",
    "CHANDRA_MODELS_DEFAULT_VERSION",
    "THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW",
]


def chandra_models_cache(func):
    """Decorator to cache outputs for a function that gets chandra_models data.

    The key used for caching the function output includes the passed arguments and
    keyword arguments, as well as the values of the environment variables below.
    This ensures that the cache is invalidated if any of these environment variables
    change:

    - CHANDRA_MODELS_REPO_DIR
    - CHANDRA_MODELS_DEFAULT_VERSION
    - THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW

    Example::

        @chandra_models_cache
        def get_aca_spec_info(version=None):
            _, info = get_data("chandra_models/xija/aca/aca_spec.json", version=version)
            return info
    """
    cache = LRUDict(capacity=32)

    @functools.wraps(func)
    def cached_func(*args, **kwargs):
        key = (
            args,
            tuple(sorted(kwargs.items())),
            tuple((name, os.environ.get(name)) for name in ENV_VAR_NAMES),
        )
        if key not in cache:
            cache[key] = func(*args, **kwargs)

        return cache[key]

    return cached_func


@contextlib.contextmanager
def get_local_repo(repo_path, version):
    """Get local version of ``repo_path`` and ensure correct clean-up."""

    def onerror(func, path, exc_info):
        os.chmod(path, 0o0777)
        try:
            func(path)
        except Exception as exc:
            print(f"Warning: temp_dir() could not remove {path} because of {exc}")

    clone = str(repo_path).startswith("https://github.com") or version is not None
    if clone:
        repo_path_local = tempfile.mkdtemp()
        repo = git.Repo.clone_from(repo_path, repo_path_local)
        if version is not None:
            repo.git.checkout(version)
    else:
        repo = git.Repo(repo_path)
        make_git_repo_safe(repo_path)
        repo_path_local = repo_path

    yield repo, repo_path_local

    repo.close()
    if clone:
        shutil.rmtree(repo_path_local, onerror=onerror)


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

    For testing purposes there are three environment variables that impact the behavior:

    - ``CHANDRA_MODELS_REPO_DIR`` or ``THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW``:
      override the default root for the chandra_models repository
    - ``CHANDRA_MODELS_DEFAULT_VERSION``: override the default repo version. You can set
      this to a fixed version in unit tests (e.g. with ``monkeypatch``), or set to a
      developement branch to test a model file update with applications like yoshi where
      specifying a version would require a long chain of API updates.

    Examples
    --------
    First we read the model specification for the ACA model. The ``get_data()`` function
    returns the text of the model spec so we need to use ``json.loads()`` to convert it
    to a dict.
    ::

        >>> import json
        >>> from astropy.io import fits
        >>> from ska_helpers import chandra_models

        >>> txt, info = chandra_models.get_data("chandra_models/xija/aca/aca_spec.json")
        >>> model_spec = json.loads(txt)
        >>> model_spec["name"]
        'aacccdpt'

    Next we read the acquisition probability model image. Since the image is a gzipped
    FITS file we need to use a helper function to read it.
    ::

        >>> def read_fits_image(file_path):
        ...     with fits.open(file_path) as hdus:
        ...         out = hdus[1].data
        ...     return out, file_path
        ...
        >>> acq_model_image, info = chandra_models.get_data(
        ...     "chandra_models/aca_acq_prob/grid-floor-2018-11.fits.gz",
        ...     read_func=read_fits_image
        ... )
        >>> acq_model_image.shape
        (141, 31, 7)

    Now let's get the version of the chandra_models repository::

        >>> chandra_models.get_repo_version()
        '3.47'

    Finally get version 3.30 of the ACA model spec from GitHub. The use of a lambda
    function to read the JSON file is compact but not recommended for production code.
    ::

        >>> model_spec_3_30, info = chandra_models.get_data(
        ...     "chandra_models/xija/aca/aca_spec.json",
        ...     version="3.30",
        ...     repo_path="https://github.com/sot/chandra_models.git",
        ...     read_func=lambda fn: (json.load(open(fn, "rb")), fn),
        ... )
        >>> model_spec_3_30 == model_spec
        False

    Parameters
    ----------
    file_path : str, Path
        Name of model
    version : str
        Tag, branch or commit of chandra_models to use (default=latest tag from repo).
        If the ``CHANDRA_MODELS_DEFAULT_VERSION`` environment variable is set then this
        is used as the default. This is useful for testing.
    repo_path : str, Path
        Path to directory or URL containing chandra_models repository (default is
        ``$SKA/data/chandra_models`` or either of the ``CHANDRA_MODELS_REPO_DIR`` or
        ``THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW`` environment variables if set).
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
    # Information about this request.
    info = {
        "call_args": {
            "file_path": str(file_path),
            "version": version,
            "repo_path": str(repo_path),
            "require_latest_version": require_latest_version,
            "timeout": timeout,
            "read_func": str(read_func),
            "read_func_kwargs": read_func_kwargs,
        }
    }

    if repo_path is None:
        repo_path = chandra_models_repo_path()

    if version is None:
        version = os.environ.get("CHANDRA_MODELS_DEFAULT_VERSION")

    # NOTE code in xija.get_model_spec.get_repo_version() which is there to handle the
    # fact that a few files are in the repo with permissions 0755 while on Parallels
    # windows they are 0644, so the tree is always dirty.
    # TODO: just fix the repo permissions.
    #
    # with temp_directory() as repo_path_local:
    #     if platform.system() == 'Windows':
    #         repo = git.Repo.clone_from(repo_path, repo_path_local)
    #     else:
    #         repo = git.Repo(repo_path)

    # Potentially work in a clone of the repo in a temporary directory, but only if
    # necessary. In particular:
    # - If the repo is remote on GitHub then we always clone to a temp dir
    # - If the repo is local and the version is not the default then we clone to a temp
    #   to allow checking out at the specified version.
    # This is all done with a context manager that ensure the repo object is
    # properly closed and that all temporary files are cleaned up. Doing this
    # on Windows was challenging. Search on slack:
    # "The process cannot access the file because it is being used"
    with get_local_repo(repo_path, version) as (repo, repo_path_local):
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
            # read_func() returns the data and the actual file path used. This is useful
            # for file globs where the file path may be a glob pattern (specified in
            # the read_func_kwargs).
            data, repo_file_path = read_func(repo_file_path, **read_func_kwargs)

        # Compute the MD5 sum of repo_file_path.
        file_bytes = repo_file_path.read_bytes().replace(b"\r", b"")
        md5 = hashlib.md5(file_bytes).hexdigest()

        # Store some info about this request in the cache.
        info.update(
            {
                "version": version,
                "commit": repo.head.commit.hexsha,
                "data_file_path": str(repo_file_path),
                "repo_path": str(repo_path),
                "md5": md5,
            }
        )
        for name in ENV_VAR_NAMES:
            info[name] = os.environ.get(name)

    return data, info


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

    # Use the THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW environment variable as a proxy
    # to determine if we are running in the MATLAB tools software environment. If so
    # the repo will not be dirty and using is_dirty() will touch a lock that will cause
    # SVN to mark the directory as modified.
    if os.environ.get('THERMAL_MODELS_DIR_FOR_MATLAB_TOOLS_SW') is None:
        if repo.is_dirty():
            raise ValueError("repo is dirty")

    tags = sorted(repo.tags, key=lambda tag: tag.commit.committed_datetime)
    tag_repo = tags[-1]

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
