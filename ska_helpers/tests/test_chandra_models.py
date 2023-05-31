# Licensed under a 3-clause BSD style license - see LICENSE.rst

import json
import re

import git
import pytest
import requests
from astropy.io import fits

from ska_helpers import chandra_models

try:
    # Fast request to see if GitHub is available
    req = requests.get(
        "https://raw.githubusercontent.com/sot/chandra_models/master/README.md",
        timeout=5,
    )
    HAS_GITHUB = req.status_code == 200
except Exception:
    HAS_GITHUB = False


ACA_SPEC_PATH = "chandra_models/xija/aca/aca_spec.json"


def read_xija_spec(fn):
    with open(fn) as fh:
        spec = json.load(fh)
    return spec, fn


def test_get_data_aca_3_30():
    # Version 3.30
    spec_txt, info = chandra_models.get_data(ACA_SPEC_PATH, version="3.30")
    spec = json.loads(spec_txt)
    assert spec["name"] == "aacccdpt"
    assert "comps" in spec
    assert spec["datestop"] == "2018:305:11:52:30.816"

    spec2, info2 = chandra_models.get_data(
        ACA_SPEC_PATH, version="3.30", read_func=read_xija_spec
    )
    assert spec == spec2

    for dct in info, info2:
        del dct["data_file_path"]
        del dct["call_args"]["read_func"]
        del dct["call_args"]["read_func_kwargs"]

    assert info == info2

    exp = {
        "call_args": {
            "file_path": "chandra_models/xija/aca/aca_spec.json",
            "version": "3.30",
            "repo_path": "None",
            "require_latest_version": False,
            "timeout": 5,
        },
        "version": "3.30",
        "commit": "94d2fa56bac1637cbfe63bcb1bc9294954379c11",
        "md5": "0e72b6402b8ed1fbaf81d5e79232461b",
    }
    assert info == exp


def test_get_data_extra_kwargs():
    def read_fits_image(file_path, hdu_num=0):
        with fits.open(file_path) as hdus:
            out = hdus[hdu_num].data
        return out, file_path

    acq_model_image, info = chandra_models.get_data(
        "chandra_models/aca_acq_prob/grid-floor-2018-11.fits.gz",
        read_func=read_fits_image,
        read_func_kwargs={"hdu_num": 1},
    )
    assert acq_model_image.shape == (141, 31, 7)


def test_get_data_aca_latest():
    # Latest version
    spec, info = chandra_models.get_data(
        ACA_SPEC_PATH, require_latest_version=HAS_GITHUB, read_func=read_xija_spec
    )
    assert spec["name"] == "aacccdpt"
    # version 3.30 value, changed in 3.31.1/3.32
    assert spec["datestop"] != "2018:305:11:52:30.816"
    assert "comps" in spec


@pytest.mark.skipif(not HAS_GITHUB, reason="GitHub not available")
def test_get_data_require_latest_version_fail():
    with pytest.raises(ValueError, match="version mismatch"):
        chandra_models.get_data(
            ACA_SPEC_PATH, version="3.30", require_latest_version=True
        )


@pytest.mark.skipif(not HAS_GITHUB, reason="GitHub not available")
def test_get_data_aca_from_github():
    # Latest version
    repo_path = "https://github.com/sot/chandra_models.git"
    spec, info = chandra_models.get_data(
        ACA_SPEC_PATH, repo_path=repo_path, version="3.30", read_func=read_xija_spec
    )
    assert spec["name"] == "aacccdpt"
    assert spec["datestop"] == "2018:305:11:52:30.816"
    assert "comps" in spec


def test_get_model_file_fail():
    with pytest.raises(
        FileNotFoundError, match=r"chandra_models file_path='xxxyyyzzz' does not exist"
    ):
        chandra_models.get_data("xxxyyyzzz")

    with pytest.raises(git.exc.NoSuchPathError):
        chandra_models.get_data(ACA_SPEC_PATH, repo_path="__NOT_A_DIRECTORY__")


def test_get_repo_version():
    version = chandra_models.get_repo_version()
    assert isinstance(version, str)
    assert re.match(r"^[0-9.]+$", version)


@pytest.mark.skipif(not HAS_GITHUB, reason="GitHub not available")
def test_check_github_version():
    version = chandra_models.get_repo_version()
    status = chandra_models.get_github_version() == version
    assert status is True

    status = chandra_models.get_github_version() == "asdf"
    assert status is False


@pytest.mark.skipif(not HAS_GITHUB, reason="GitHub not available")
def test_check_github_timeout():
    # Force timeout
    status = chandra_models.get_github_version(timeout=0.00001)
    assert status is None


@pytest.mark.skipif(not HAS_GITHUB, reason="GitHub not available")
def test_check_github_bad_url():
    with pytest.raises(requests.ConnectionError):
        chandra_models.get_github_version(url="https://______bad_url______")
