import ska_helpers
from ska_helpers.docs import get_conf_module
import os
from pathlib import Path


def test_get_conf_module():
    context = {
        "project": "ska_helpers",
        "author": "Tom A",
        "import_path": os.path.abspath(".."),
    }
    conf = get_conf_module(context)
    assert conf.project == context["project"]
    assert conf.author == context["author"]
    assert conf.import_path == os.path.abspath("..")
    assert conf.template_dir == str(
        Path(ska_helpers.docs.__file__).parent.absolute() / "_templates"
    )
    assert conf.version == ska_helpers.__version__
    assert conf.release == ska_helpers.__version__
