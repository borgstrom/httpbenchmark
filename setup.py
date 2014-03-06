#!/usr/bin/env python

from setuptools import setup

import re
import sys

# load our version from our init file
init_data = open('httpbenchmark/__init__.py').read()
matches = re.search(r"__version__ = '([^']+)'", init_data, re.M)
if matches:
    version = matches.group(1)
else:
    raise RuntimeError("Unable to load version")

requirements = [
    'numpy>=1.6,<2.0',
    'tornado>=2.3,<3.0',
    'pycurl>=7.19,<7.20'
]
if sys.version_info < (2, 7):
    requirements.append('argparse')

setup(
    name='httpbenchmark',
    packages=['httpbenchmark'],
    scripts=['scripts/pb'],
    include_package_data=True,
    version=version,
    license="Apache License, Version 2.0",
    description='Python HTTP Benchmarking Tool',
    long_description=open('README.rst').read(),
    author='Evan Borgstrom',
    author_email='evan@borgstrom.ca',
    url='https://github.com/borgstrom/httpbenchmark',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=requirements
)
