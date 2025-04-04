"""Provide base conf.py for Sphinx documentation for all Ska projects."""

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import importlib
import os
import re
import sys
from pathlib import Path

template_dir = str(Path(__file__).parent.absolute() / "_templates")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

# `project` and `author` are normally injected into the namespace by the calling conf.py
# via ska_helpers.docs.get_conf_module(context).
project = globals().get("project", "None")
author = globals().get("author", "None")
year = str(datetime.datetime.now().year)
copyright = f"{year}, Smithsonian Astrophysical Observatory"

# -- Path setup --------------------------------------------------------------
sys.path.insert(0, os.path.abspath(".."))

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.imgmath",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "matplotlib.sphinxext.plot_directive",
    "numpydoc",
    "autoapi.extension",
]

templates_path = [template_dir]

# Version information from the package. Clip anything in the version beyond dev number,
# e.g. 0.1.0.dev12+g1234567+d12312311 => 0.1.0.dev12. This is to avoid the version
# stomping on the top menu.
pkg = importlib.import_module(project)
version = re.sub(r"(dev\d+).+", r"\1", pkg.__version__)
release = version

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Do not show type hints in the documentation
autodoc_typehints = "none"

# -- Options for HTML output ---------------------------------------------------
html_baseurl = f"https://sot.github.io/{project}/"

# The theme to use for HTML and HTML Help pages.
html_theme = "pydata_sphinx_theme"

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": f"https://github.com/sot/{project}",
            "icon": "fab fa-github-square",
        },
    ],
    "navbar_start": ["navbar-project-version"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "secondary_sidebar_items": ["page-toc"],
}

# No left sidebar
html_sidebars = {"**": []}

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# Copybutton configuration
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True

# Plot directive configuration
plot_formats = ["png"]
plot_html_show_formats = False
plot_html_show_source_link = False
plot_pre_code = """\
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.style.use("bmh")
"""

# Don't show summaries of the members in each class along with the
# class' docstring
numpydoc_show_class_members = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "astropy": ("https://docs.astropy.org/en/stable/", None),
}

# Intersphinx for Ska packages that live at https://sot.github.io/{project}
ska_projects = [
    "aca_view",
    "agasc",
    "annie",
    "astromon",
    "chandra_aca",
    "chandra_maneuver",
    "chandra_time",
    "cheta",
    "cxotime",
    "find_attitude",
    "kadi",
    "maude",
    "mica",
    "parse_cm",
    "proseco",
    "Quaternion",
    "ska_arc5gl",
    "ska_astro",
    "ska_dbi",
    "ska_file",
    "ska_ftp",
    "ska_helpers",
    "ska_matplotlib",
    "ska_numpy",
    "ska_quatutil",
    "ska_shell",
    "ska_sun",
    "ska_tdb",
    "skare3_tools",
    "testr",
    "xija",
]

# Set up intersphinx, except for the current project
for ska_project in set(ska_projects) - set([project]):
    intersphinx_mapping[ska_project] = (f"https://sot.github.io/{ska_project}/", None)

autoapi_dirs = [f"../{project}"]
autoapi_root = "api"
autoapi_template_dir = template_dir
autoapi_own_page_level = "function"
autoapi_ignore = ["*/test_*.py", "*/conftest.py"]
