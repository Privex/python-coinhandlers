#!/usr/bin/env python3
"""
+===================================================+
|                 © 2019 Privex Inc.                |
|               https://www.privex.io               |
+===================================================+
|                                                   |
|        Python Cryptocurrency Handlers             |
|        License: X11/MIT                           |
|                                                   |
|        Core Developer(s):                         |
|                                                   |
|          (+)  Chris (@someguy123) [Privex]        |
|                                                   |
+===================================================+

Python Cryptocurrency Handlers - Various classes for handling sending/receiving cryptocurrencies
Copyright (c) 2019    Privex Inc. ( https://www.privex.io )

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation 
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, 
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS 
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Except as contained in this notice, the name(s) of the above copyright holders shall not be used in advertising or 
otherwise to promote the sale, use or other dealings in this Software without prior written authorization.
"""

from setuptools import setup, find_packages
from privex.coin_handlers import VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='privex_coinhandlers',

    version=VERSION,

    description='Various classes for handling sending/receiving cryptocurrencies',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Privex/python-coinhandlers",
    author='Chris (Someguy123) @ Privex',
    author_email='chris@privex.io',

    license='MIT',
    install_requires=[
        'requests>=2.20.1',
        'privex-jsonrpc>=1.1.2',
        'privex-helpers>=1.3.3',
        'golos-python>=1.0.3',
        'python-dateutil',
        'pytz',
        'attrs',
    ],
    packages=find_packages(exclude=['tests', 'test.*']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
