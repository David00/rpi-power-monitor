---
layout: default
title: Acquiring the Hardware
---

## Acquiring the Hardware

Here's a quick summary of everything you'll need:

* Raspberry Pi 4B with 2GB+ of RAM. A 3B+ will also work, but is not ideal with the 1GB of RAM.
* High Endurance microSD card at least 32GB.
* [Factory assembled power monitor PCB](https://power-monitor.dalbrecht.tech/product/pre-soldered-pcb-v2/), or the [DIY self-assembly kit](https://power-monitor.dalbrecht.tech/product/diy-power-monitor-kit/)
* [Current Transformers](https://power-monitor.dalbrecht.tech/product-category/current-transformers/) (see ["Selecting CTs"](#selecting-cts) below)
* [9V AC to AC Supply](https://power-monitor.dalbrecht.tech/product/9v-ac-transformer-north-america-only/)

Purchasing items directly from my shop in the links allows me to continuously maintain this open source project, work on improvements, and provide user support. I am very thankful for your support!


### Selecting CTs

With the list that you've written down from the [previous step](./create-your-plan), you should know the ratings of the circuits you intend to monitor.

When choosing a CT, select a CT with a rating that is at or slightly above the rating of the breaker.  The diameter of the CT opening increases as the rating of the sensor goes up. Here is a quick summary:

* 20A - 60A: 10mm
* 100A - 120A: 16mm
* 150A - 250A: 24mm

It is possible that a conductor is too large for the sensor according to the breaker rating, so you should also have the electrician double check the diameter of each wire that you want to order and make sure the selected sensor will fit.


### Using a different CT

The CTs in my shop are manufactured specifically for my project. It is possible to use other sensors, but it's not always ideal.  If using a sensor you have on hand, it should be of the "current-output" type with a maximum output of ~50mA.  If your sensor is the "voltage-output" type, the ideal (and absolute maximum) output is 1.65V.  Do not use a sensor that puts out 5V as this will likely cause damage to the ADC.


### 9V AC Supply

The 9V AC to AC transformer provides the grid voltage reading to the power monitor.  It does not power the Raspberry Pi.  I only stock North American compatible AC transformers, so if you have a different grid, you'll need to source one yourself.  The required specs are:

Output: 9V AC, 500mA
Plug type: 2.1 x 5.5mm, center positive


### Summary

Once you have your Pi and microSD card, you can move onto [the software](./install-the-software).