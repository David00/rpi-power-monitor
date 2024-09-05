---
nav_order: 1
---

## Welcome to the Power Monitor for Raspberry Pi!

The Raspberry Pi Power Monitor is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time, including power consumption, generation, and net-status. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

This project is derived from and inspired by the resources located at https://learn.openenergymonitor.org.


## What does it do?

This code accompanies DIY circuitry (see the references above) that supports monitoring of up to 6 current transformers and one AC voltage reading. The individual readings are then used in calculations to provide real data on consumption and generation, including the following key metrics:

 * Total home consumption
 * Total solar PV generation
 * Net home consumption
 * Net home generation
 * Total current, voltage, power, and power factor values
 * Individual current transformer readings


## Where can I get it?

Please see my website to order the power monitor PCB and current sensors:

[https://power-monitor.dalbrecht.tech/](https://power-monitor.dalbrecht.tech/)


## Safety

This project interfaces with high voltage electrical systems and discusses working in and around a main electrical panel. I would recommend hiring a licensed electrician to install the CTs on your high voltage lines. Any processes outlined in this project are taken at your own risk and I cannot be held liable for personal injury or property damage.

## Quickstart / Setup Guide

1. [Create Your Plan](docs/general/create-your-plan)
2. [Acquire the Hardware](docs/general/acquire-the-hardware)
3. [Install the Software](docs/general/install-the-software)
4. [Install the Harware](docs/general/hardware-installation)
5. [Calibration](docs/latest/calibration)
6. [Dashboards](docs/latest/accessing-the-dashboard)