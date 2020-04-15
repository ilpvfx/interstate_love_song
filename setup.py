# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from setuptools.command.test import test

import os
import sys

if sys.version_info < (3, 7):
    sys.exit("Sorry, Python < 3.7 is not supported")

version_path = os.path.join(
    os.path.dirname(__file__), "source", "interstate_love_song", "_version.py",
)

with open(version_path) as version_file:
    env = {}
    exec(version_file.read(), env)
    VERSION = env["VERSION"]

ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

SOURCE_PATH = os.path.join(ROOT_PATH, "source")

setup(
    name="interstate_love_song",
    version=VERSION,
    packages=find_packages(SOURCE_PATH),
    author="Eric Hermelin, Simon Otter, Fredrik Brännbacka",
    author_email="eric.hermelin@ilpvfx.com, simon.otter@ilpvfx.com, fredrik.brannbacka@ilpvfx.com",
    python_requires=">3.6",
    entry_points={"console_scripts": ["interstate_love_song=interstate_love_song.__main__:main",],},
    install_requires=[
        "falcon >= 2, < 3",
        "defusedxml==0.6.0",
        "beaker >= 1, < 2",
        "falcon_middleware_beaker==0.0.1",
        "requests >= 2, < 3",
    ],
    package_dir={"": "source",},
)
