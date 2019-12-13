# Licensed under a 3-clause BSD style license - see LICENSE.rst
from distutils.core import setup

try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

setup(name='ska_helpers',
      description='Utilities for SKA packages',
      author='Javier Gonzalez',
      author_email='javier.gonzalez@cfa.harvard.edu',
      url='http://cxc.harvard.edu/mta/ASPECT/tool_doc/ska_helpers.html',
      packages=['ska_helpers'],
      tests_require=['pytest'],
	  use_scm_version=True,
      setup_requires=['setuptools_scm'],
      cmdclass=cmdclass,
      )
