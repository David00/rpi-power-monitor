---
title: Software Installation
parent: General
grand_parent: Documentation
nav_order: 3
layout: default
---


## Software Installation

The recommended way to setup and use this project is with the provided custom [Raspberry Pi OS Image](https://github.com/David00/rpi-power-monitor/releases). 
https://github.com/David00/rpi-power-monitor/releases/tag/v0.2.0

The provided Pi OS image is simply the stock Raspberry Pi OS Lite image with all the dependencies pre-installed, and it is suitable for offline installations. Simply download the file and use Raspberry Pi Imager to write the image to your microSD card.

For advanced users, you can install the software manually. Please see manual-installation.md.

{: .note-aqua }
The custom image is command-line only (no desktop). You should be familiar with using SSH and basic command line instructions.


### Setup

See the Software Installation page for the specific release that you are using. The latest release is {{ site.latest-version }} and its software installation page is here:

[{{ site.latest-version }} - Software Installation](/docs/{{ site.latest-version }}/configuration)

In v0.3.0, I introduced a new configuration file named `config.toml`. This file is included in the custom OS image, but has to be created if you chose the manual install method.