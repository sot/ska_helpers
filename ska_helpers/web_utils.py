# Licensed under a 3-clause BSD style license - see LICENSE.rst
import re
from pathlib import Path
from urllib.parse import urljoin

import requests


def get_last_referenced_web_image(
    url: str, img_src_pattern: str, cache_dir: str | Path
) -> Path:
    """
    Get the image from a web page matching a pattern and download it.

    This caches the files to avoid downloading files we already have.
    This works for the case when the image referenced in the HTML has a file name
    that is changed when the file is updated.

    Parameters
    ----------
    url : str
        The URL of the web page to get the image from.
    img_src_pattern : str
        The regular expression pattern to match the image source.
    cache_dir : str or Path
        The directory to cache the image in. If not supplied, a default
        directory will be used in the user's home directory.

    Returns
    -------
    Path
        The path to the cached image.
    """

    # Make cache directory
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Fetch the web page and get the html
    response = requests.get(url)
    html = response.text

    # get absolute url of the image that matches the supplied pattern
    pattern = re.compile(img_src_pattern)
    match = pattern.search(html)
    if match:
        img_src = match.group(1)
        img_url = urljoin(url, img_src)
    else:
        raise ValueError("No image found matching the pattern")

    # What is the file name of the image?
    img_filename = Path(img_url).name

    # If the image is already in the cache, return it
    cached_image = cache_dir / img_filename
    if cached_image.exists():
        return cached_image

    # Delete any files in the cache directory
    for file in cache_dir.iterdir():
        file.unlink()

    # Download the new image and save it to the cache directory
    response = requests.get(img_url)
    with open(cached_image, "wb") as f:
        f.write(response.content)

    # And return the cached image path
    return cached_image
