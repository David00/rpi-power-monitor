---
title: v0.1.0
parent: Documentation
nav_order: 12
has_children: true
layout: default
---

# v0.1.0 Documentation

Release Date: May 24, 2021

## Introduction

The Raspberry Pi Power Monitor is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time (<0.5 second intervals), including consumption, generation, and net-production. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

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

1. [Create Your Plan](./create-your-plan)
2. [Acquire the Hardware](./acquire-the-hardware)
3. [Install the Software](./install-the-software)
4. [Install the Harware](./install-the-harware)
5. [Calibration](./calibration)
6. [Dashboards](./dashboards)