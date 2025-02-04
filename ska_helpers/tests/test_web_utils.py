import shutil
import tempfile
from pathlib import Path

from PIL import Image

from ska_helpers.web_utils import get_last_referenced_web_image

# This is an image used in Replan Central
solar_flare_url = "https://www.solen.info/solar/index.html"
solar_flare_pattern = r"(images/AR_CH_\d{8}.png)"


def test_solar_flare_fetch_new():
    """
    Test that the function fetches a new image and saves it to the cache directory.
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Call the function with the temporary directory
        image_path = get_last_referenced_web_image(
            solar_flare_url, solar_flare_pattern, tmpdirname
        )
        assert image_path.exists()
        # Check that the fetched file is a PNG image
        assert image_path.suffix == ".png"
        # And confirm it looks like a png
        img = Image.open(image_path)
        img.verify()


def test_solar_flare_fetch_cache():
    """
    Test that the function returns the cached image if it exists.
    """
    tempdir1 = tempfile.mkdtemp()
    image_path1 = get_last_referenced_web_image(
        solar_flare_url, solar_flare_pattern, tempdir1
    )
    # What is the file name of the image?
    img_filename = Path(image_path1).name

    tempdir2 = tempfile.mkdtemp()
    # Make a new file with the same name in the new directory
    new_file = Path(tempdir2) / img_filename
    # But just make this a dummy file and not a png
    dummy_text = "this is a dummy file"
    with open(new_file, "wb") as f:
        f.write(dummy_text.encode())

    # Now call the function with the new temporary directory
    image_path2 = get_last_referenced_web_image(
        solar_flare_url, solar_flare_pattern, tempdir2
    )
    # And read it to confirm it is the same file
    with open(image_path2, "rb") as f:
        assert f.read() == dummy_text.encode()

    # Clean up the temporary directories
    shutil.rmtree(tempdir1)
    shutil.rmtree(tempdir2)
