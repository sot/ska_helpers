"""Provide base conf.py for Sphinx documentation for all Ska project.

Example usage in docs/conf.py. This is available in ``skare3/templates/conf.py``::

  import ska_helpers.docs
  
  # Get variables from the ska_helpers.docs.conf module that are not private, modules, or
  # classes and inject into this namespace. This provides the base configuration for the
  # Sphinx documentation.
  globals().update(
      ska_helpers.docs.get_conf_module_vars(
          project="chandra_aca",
          author="Tom Aldcroft",
      )
  )
  
  # Add any custom configuration here

"""
import sys
import importlib.util
import inspect

def get_conf_module(context):
    """Return the ska_helpers.docs.conf module.

    Parameters
    ----------
    context : dict
        A dictionary of context variables to inject into the conf module.
        This is typically the project name and author.

    Returns
    -------
    module
        The ska_helpers.docs.conf module with the context variables injected.
    """
    name = "ska_helpers.docs.conf"
    spec = importlib.util.find_spec(name)
    conf = importlib.util.module_from_spec(spec)

    for k, v in context.items():
        setattr(conf, k, v)

    sys.modules[name] = conf
    spec.loader.exec_module(conf)
    return conf


def get_conf_module_vars(**context):
    """Return the configuration variables from the ska_helpers.docs.conf module.

    Parameters
    ----------
    context : dict
        A dictionary of context variables to inject into the conf module.
        This is typically the project name, author, and import path.
        The import path is used to set the sys.path for the conf module.

    Returns
    -------
    dict
        A dictionary of variables from the ska_helpers.docs.conf module.
        This includes the project name, author, and import path.
    """
    conf = get_conf_module(context)

    # Extract the variables from the conf module that are not private, modules, or
    # classes and return that as a dict.
    vars_ = {
        k: v
        for k, v in vars(conf).items()
        if not k.startswith("_") and not inspect.ismodule(v) and not inspect.isclass(v)
    }
    return vars_
