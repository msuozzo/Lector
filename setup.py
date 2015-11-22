#!/usr/bin/env python  #pylint: disable=missing-docstring

import ast
import os
import re
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from setuptools import setup


def open_(fname, *args, **kwargs):
    return open(os.path.join(os.path.dirname(__file__), fname), *args, **kwargs)

# Extract the version string from lector/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open_('lector/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

# Extract the package requirements from requirements.txt
with open_('requirements.txt') as f:
    requires = f.read().splitlines()

setup(name='Lector',
      version=version,
      description='An API for Amazon Kindle Data',
      author='Matthew Suozzo',
      author_email='iratus.litteris@gmail.com',
      url='https://github.com/msuozzo/Lector',
      packages=['lector'],
      install_requires=requires,
      license='MIT'
     )
