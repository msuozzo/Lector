#!/usr/bin/env python  #pylint: disable=missing-docstring

import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import lector

open_ = lambda fname: open(os.path.join(os.path.dirname(__file__), fname))

with open_('requirements.txt') as f:
    requires = f.read().splitlines()

setup(name='Lector',
      version=lector.__version__,
      description='An API for Amazon Kindle Data',
      author='Matthew Suozzo',
      author_email='iratus.litteris@gmail.com',
      url='https://github.com/msuozzo/Lector',
      packages=['lector'],
      install_requires=requires,
      license='MIT'
     )
