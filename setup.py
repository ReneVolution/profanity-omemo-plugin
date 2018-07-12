#!/usr/bin/env python
from __future__ import print_function

import platform
from codecs import open
from glob import glob
from os import path
from os.path import basename
from os.path import splitext

from setuptools import setup, find_packages
from setuptools.command.install import install

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

requirements = [
        'python-axolotl>=0.1.7',
        'protobuf>=3.0.0b2,<3.2'
    ]

if platform.python_implementation() == 'PyPy':
    requirements += ['pycrypto']
else:
    requirements += ['cryptography>=1.1']


setup(
    name='profanity-omemo-plugin',
    version='0.0.1',
    description=('A plugin to enable OMEMO encryption for '
                 'the profanity messenger.'),

    long_description=long_description,
    url='https://github.com/ReneVolution/profanity-omemo-plugin.git',
    author='Rene Calles',
    author_email='info@renevolution.com',
    license='GPL',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Security :: Cryptography',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',  # noqa
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='omemo encryption messaging profanity xmpp jabber',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    data_files=[('profanity_omemo_plugin', ['deploy/prof_omemo_plugin.py'])],
    install_requires=requirements,
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'mock'],
)
