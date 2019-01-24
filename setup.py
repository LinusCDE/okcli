#!/usr/bin/env python

import re
import ast
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('oracli/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

description = 'CLI for Oracle DB Database. With auto-completion and syntax highlighting.'


def get_requirements():
    with open('requirements.txt', 'r') as f:
        return f.read().splitlines()


setup(
    name='oracli',
    version=version,
    packages=find_packages(),
    description=description,
    long_description=description,
    install_requires=get_requirements(),
    include_package_data=True,
    entry_points={
        'console_scripts': ['oracli = oracli.main:cli'],
    },
)
