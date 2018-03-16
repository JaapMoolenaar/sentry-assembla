# coding=utf-8
"""This module installs the Sentry.io Assembla integration plugin"""

from setuptools import setup, find_packages

setup(
    name='sentry_assembla',
    version='0.0.1',
    author='Jaap Moolenaar',
    url='https://github.com/JaapMoolenaar/sentry-assembla',
    description='A Sentry.io plugin for Assembla integration',
    keywords='sentry-assembla sentry assembla',
    long_description=open('README.md').read(),
    packages=find_packages(),
    dependency_links=[],
    license='MIT',
    include_package_data=True,
    entry_points={
        'sentry.plugins': ['sentry_assembla=sentry_assembla.plugin:AssemblaPlugin']
    },
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
