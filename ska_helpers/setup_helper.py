# Licensed under a 3-clause BSD style license - see LICENSE.rst


def duplicate_package_info(vals, name_in, name_out):
    """
    Duplicate a list or dict of values inplace, replacing ``name_in`` with ``name_out``.

    Normally used in setup.py for making a namespace package that copies a flat one.
    For an example see setup.py in the ska_sun or Ska.Sun repo.

    :param vals: list or dict of values
    :param name_in: string to replace at start of each value
    :param name_out: output string
    """
    import re

    for name in list(vals):
        new_name = re.sub(f"^{name_in}", name_out, name)
        if isinstance(vals, dict):
            vals[new_name] = vals[name]
        else:
            vals.append(new_name)
