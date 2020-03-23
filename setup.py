# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from setuptools.command.test import test

import os
import sys

if sys.version_info < (3, 7):
    sys.exit("Sorry, Python < 3.7 is not supported")

sys.executable = "/bin/env python"

version_path = os.path.join(
    os.path.dirname(__file__), "source", "interstate_love_song", "_version.py",
)
with open(version_path) as version_file:
    env = {}
    exec(version_file.read(), env)
    VERSION = env["VERSION"]

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

SOURCE_PATH = os.path.join(ROOT_PATH, "source")

TESTS_PATH = os.path.join(ROOT_PATH, "tests")


class PyTest(test):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        super(PyTest, self).initialize_options()

        self.pytest_args = "-v {path}".format(path=TESTS_PATH)

    def run_tests(self):
        import shlex
        import pytest

        if __name__ == "__main__":
            errno = pytest.main(shlex.split(self.pytest_args))

            sys.exit(errno)


cmdclass = {"test": PyTest}

setup_requires = []
if "test" in sys.argv:
    setup_requires.append("pytest==5")
    setup_requires.append("xmldiff >= 2")
    setup_requires.append("httpretty==0.9.7")

setup(
    name="interstate_love_song",
    version=VERSION,
    packages=find_packages(SOURCE_PATH),
    author="Eric Hermelin, Simon Otter, Fredrik Brännbacka",
    author_email="eric.hermelin@ilpvfx.com, simon.otter@ilpvfx.com, fredrik.brannbacka@ilpvfx.com",
    python_requires=">3.6",
    entry_points={"console_scripts": ["interstate_love_song=interstate_love_song",],},
    setup_requires=setup_requires,
    install_requires=[
        "falcon >= 2, < 3",
        "defusedxml==0.6.0",
        "beaker >= 1, < 2",
        "falcon_middleware_beaker==0.0.1",
        "requests >= 2, < 3",
    ],
    package_dir={"": "source",},
    cmdclass=cmdclass,
)
