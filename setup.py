#!/usr/bin/env python

from setuptools import setup
import os.path

with open(os.path.join(os.path.dirname(__file__), 'sqlconmanager/__init__.py')) as pyinit:
    for line in pyinit.readlines():
        if line.startswith('__version__'):
            exec (line.strip())
            break
        else:
            raise IOError("Missing __version__ definition in __init__.py")

INSTALL_REQUIRES = [
    "sqlsoup",
    "sqlalchemy",
    "pyyaml",
    "nose"
]

setup(
    name="sqlconmanager",
    version=__version__,
    author="Mike Sze",
    author_email="msze@veriskclimate.com",
    description="A module for initiating and managing connections to an sql database",
    packages=['sqlconmanager', 'sqlconmanager.resources', 'sqlconmanager.tests'],
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    scripts=['sqlconmanager/connection_manager.py'],
    setup_requires=['nose'],
    test_suite='nose.collector',
    package_data={'sqlconmanager': ['resources/dbconfig.yaml',
                                 'tests/testdbconfig.yaml']},
)