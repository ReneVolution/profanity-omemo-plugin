from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.test import test as TestCommand

# To use a consistent encoding
import sys
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


class CustomInstallCommand(install):
    def run(self):
        # Call parent
        install.do_egg_install(self)

        # Install the actual profanity-omemo.py to the profanity plugins folder.
        print "do post install stuff here..."


setup(
    name='profanity-omemo-plugin',
    version='0.0.1',
    description=('A plugin to enable OMEMO encryption for '
                 'the profanity messenger.'),

    long_description=long_description,
    url='https://github.com/ReneVolution/profanity-omemo-plugin.git',
    author='Rene Calles',
    author_email='info@renevolution.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Security :: Cryptography',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.3',
        # 'Programming Language :: Python :: 3.4',
        # 'Programming Language :: Python :: 3.5',
    ],

    keywords='omemo encryption messaging profanity xmpp jabber',
    packages=find_packages(exclude=['deploy', 'docs', 'tests']),
    data_files=[('profanity_omemo_plugin', ['deploy/prof_omemo_plugin.py'])],
    install_requires=['python-omemo'],
    tests_require=['pytest'],
    dependency_links=['git+https://github.com/omemo/python-omemo.git@158b0a236d93b10d9c3b7ecea6c53254967f7b01#egg=python-omemo-0'],  # noqa

    # Extend the install command with a post_install command
    cmdclass={'install': CustomInstallCommand, 'test': PyTest},
)
