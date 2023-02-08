---

title: FAQ
nav_order: 10

---

# FAQ
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>

## General


## Hardware

<details markdown="block">
<summary id="can-i-use-to-monitor-X" class="fs-5">Can I use this to monitor _____?</summary>
{: .text-delta }
This project is only capable of monitoring AC power systems, including North American 120V 60Hz grids, and Eurasian 230V 50 Hz grids.

Adaptations to monitor other systems like DC power, gas, and water, are not supported.

</details>


## Software

<details markdown="block">
<summary id="how-do-i-determine-which-software-version-i-have" class="fs-5">How do I determine which software version I have?</summary>
{: .text-delta }

The most recent versions (v0.2.0 and above), you can run the following command in your terminal:

`pip list --format=freeze | grep "rpi-power-monitor"`

If this doesn't show anything, then you are likely on an old pre-v0.2.0 version.

If you installed the custom OS, the OS build version can be determined by running the following command:

`cat /root/rpi_power_monitor_os-version.txt`

If you see `No such file or directory`, then you are likely on the original v0.1.0 version that did not have this file.

Unless you have updated your power monitor software, the OS build version should match the power monitor code version.

</details>


## Troubleshooting
