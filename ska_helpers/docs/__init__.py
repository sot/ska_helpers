"""Provide base conf.py for Sphinx documentation for all Ska project.

Example usage in docs/conf.py. This is available in ``skare3/templates/conf.py``::

    import os

    import ska_helpers.docs

    context = {
        "project": "parse_cm",
        "author": "Tom Aldcroft",
        "import_path": os.path.abspath(".."),
    }

    # Get the base Ska conf.py from ska_helpers.docs.conf, putting `context` into the
    # conf.py namespace.
    conf = ska_helpers.docs.get_conf_module(context)

    # Inject all the symbols from the ska_helpers.docs.conf module into this namespace.
    globals().update({k: v for k, v in vars(conf).items() if not k.startswith("_")})
"""
import sys
import importlib.util

def get_conf_module(context):
    name = "ska_helpers.docs.conf"
    spec = importlib.util.find_spec(name)
    conf = importlib.util.module_from_spec(spec)

    for k, v in context.items():
        setattr(conf, k, v)

    sys.modules[name] = conf
    spec.loader.exec_module(conf)
    return conf
