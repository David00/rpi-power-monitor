"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="rpi-power-monitor",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description="Raspberry Pi Power Monitor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # The project's main homepage.
    url="https://github.com/David00/rpi-power-monitor",
    # Author details
    author="David00",
    author_email="github@dalbrecht.tech",
    install_requires=["spidev==3.5"],
    # Choose your license
    license="GNU General Public License (GPLv3)",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: GNU General Public License (GPLv3)",
        "Programming Language :: Python :: 3",
    ],
    # What does your project relate to?
    keywords="raspberry pi power monitor",
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    py_modules=["power_monitor"],
)
