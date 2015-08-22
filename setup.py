#!/usr/bin/env python  #pylint: disable=missing-docstring

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import kindle_api

setup(name='Kindle API',
      version=kindle_api.__version__,
      description='Interface for Amazon\'s Kindle Data',
      author='Matthew Suozzo',
      author_email='matthew.suozzo@gmail.com',
      url='https://github.com/msuozzo/kindle_api',
      packages=['kindle_api'],
      license='MIT'
     )
