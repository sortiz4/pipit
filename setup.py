#!/usr/bin/env python
from pipit import Command
from setuptools import setup

setup(
    name=Command.name,
    version=Command.version,
    description='Yet another Python dependency manager.',
    author='Steven Ortiz',
    url='https://github.com/sortiz4/pipit',
    packages=['pipit'],
    entry_points={'console_scripts': ['pipit = pipit:main']},
)
