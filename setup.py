#!/usr/bin/env python
from setuptools import setup

setup(
    name='pipit',
    version='1.0',
    description='Yet another Python dependency manager.',
    author='Steven Ortiz',
    url='https://github.com/sortiz4/pipit',
    packages=['pipit'],
    entry_points={'console_scripts': ['pipit = pipit:main']},
)
