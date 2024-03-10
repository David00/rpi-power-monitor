"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# To use a consistent encoding
from codecs import open
from os import path

# Always prefer setuptools over distutils
from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="rpi_power_monitor",
    version='0.3.0',
    description="Raspberry Pi Power Monitor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/David00/rpi-power-monitor",
    author="David00",
    author_email="github@dalbrecht.tech",
    install_requires=[
        "influxdb==5.2.3",
        "prettytable==0.7.2",
        "plotly==4.5.4",
        "spidev==3.6",
        "requests==2.31.0",
        "tomli==2.0.1"
    ],
    license="GNU General Public License (GPLv3)",
    packages=["rpi_power_monitor"],
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
