# -*- coding: utf-8 -*-

from distutils.core import setup
from setuptools import find_packages

setup(name='TaskStackIndicator',
    version='0.5',
    description='Task stack indicator',
    author='David García Goñi',
    author_email='dagargo@gmail.com',
    url='https://github.com/dagargo/task-stack-indicator',
    packages=find_packages(exclude=['doc', 'tests']),
    package_data={'task_stack_indicator': ['resources/*']},
    license='GNU General Public License v3 (GPLv3)',
    install_requires=[],
    test_suite='tests',
    tests_require=[]
)
