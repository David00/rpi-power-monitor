"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# To use a consistent encoding
from codecs import open
from os import path

# Always prefer setuptools over distutils
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="rpi_power_monitor",
    version='0.4.0',
    description="Raspberry Pi Power Monitor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/David00/rpi-power-monitor",
    author="David00",
    author_email="github@dalbrecht.tech",
    install_requires=[
        "influxdb==5.3.2",
        "influxdb-client>=1.48.0",
        "prettytable==3.12.0",
        "plotly==4.14.3",
        "spidev==3.6",
        "requests==2.32.3",
        "tomli==2.2.1",
        "setuptools>=75"
    ],
    license="GNU General Public License (GPLv3)",
    packages=find_packages(include=['rpi_power_monitor', 'rpi_power_monitor.*']),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Hardware",
        "License :: OSI Approved :: GNU General Public License (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
    ],
    keywords="raspberry pi power monitor"
)
