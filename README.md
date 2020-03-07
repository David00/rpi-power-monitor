# Raspberry Pi Whole Home Power Monitor


This project is derived from the resources located at https://openenergymonitor.org, and, more specifically, the theory described in the section here:
https://learn.openenergymonitor.org/electricity-monitoring/ac-power-theory/introduction

The code in this repository is still being developed and at this point (March 2020) in time, only basic functionality exists.

---

### What does it do?

This code accompanies DIY circuitry (see the references above) that supports monitoring of 4 current transformers and one AC voltage reading, with an end goal of calculating, storing, and displaying whole-home power usage and solar photovoltaic generation.

In my particular case, 3 CT sensors will be used for monitoring the house consumption via two main 120V legs in my electrical panel and a smaller 100A subpanel.  The 4th CT sensor will be used to monitor my solar PV feed into the main panel.

---

### More Info

As I continue working on this project, I intend on sharing a complete list of hardware components and a summary of my experiences.


---

### Credits

* [OpenEnergyMonitor](https://openenergymonitor.org) and forum member Robert.Wall for guidance and support

* The `spidev` project on PyPi for providing the interface to read an analog to digital converter
