#!/usr/bin/env python  #pylint: disable=missing-docstring

import os
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import kindle_api

open_ = lambda fname: open(os.path.join(os.path.dirname(__file__), fname))

with open_('requirements.txt') as f:
    requires = f.read().splitlines()

setup(name='Kindle API',
      version=kindle_api.__version__,
      description='Interface for Amazon\'s Kindle Data',
      author='Matthew Suozzo',
      author_email='iratus.litteris@gmail.com',
      url='https://github.com/msuozzo/kindle_api',
      packages=['kindle_api'],
      install_requires=requires,
      license='MIT'
     )
