#!/usr/bin/env python

import distutils.cmd
import subprocess
import sys

import os
import re
import shutil
from setuptools import setup, find_packages
from setuptools.command.test import test

NAME = "interstate_love_song"

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

SOURCE_PATH = os.path.join(ROOT_PATH, "source")

TESTS_PATH = os.path.join(ROOT_PATH, "tests")

with open(os.path.join(SOURCE_PATH, NAME, "_version.py")) as _version_file:
    VERSION = re.match(r".*__version__ = .*\'((.*?))\'.*", _version_file.read(), re.DOTALL).group(1)


class PyTest(test):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        test.initialize_options(self)

        self.pytest_args = "--cov={0} -v {1}".format(NAME, TESTS_PATH)

    def run_tests(self):
        import shlex
        import pytest

        if "MM_TEST_DB_URL" not in os.environ:
            raise EnvironmentError('environment variable "MM_TEST_DB_URL" must be defined.')

        errno = pytest.main(shlex.split(self.pytest_args))

        sys.exit(errno)


setup(
    name=NAME,
    version=VERSION,
    author="eric hermelin",
    author_email="eric.hermelin@gmail.com",
    packages=find_packages(SOURCE_PATH),
    package_dir={"": "source"},
    setup_requires=["pytest", "pytest-cov", "snapshottest",],
    install_requires=["falcon-cors", "falcon", "falcon-auth", "kerberos",],
    cmdclass={"test": PyTest},
    dependency_links=[],
    package_data={NAME: ["_static/*.js", "_static/*.css"]},
    include_package_data=True,
)
