# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

setup(name='ska_helpers',
      description='Utilities for ska packages',
      author='Javier Gonzalez',
      author_email='javier.gonzalez@cfa.harvard.edu',
      url='http://cxc.harvard.edu/mta/ASPECT/tool_doc/ska_helpers.html',
      packages=['ska_helpers'],
      tests_require=['pytest'],
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      cmdclass=cmdclass,
      )
