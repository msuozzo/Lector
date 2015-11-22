"""
Lector
~~~~~~~~~~

Interface for Amazon Kindle Data
"""

__version__ = '0.0.3a'

from .reader import KindleAPIError, ConnectionError, InitError,\
        KindleBook, ReadingProgress, KindleCloudReaderAPI
