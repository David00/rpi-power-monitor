# Power Monitor HAT (for Raspberry Pi)

This project is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time, including accurate consumption, generation, and net-production. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

This project is derived from and inspired by the resources located at https://learn.openenergymonitor.org. 

---

## Where can I get it?

I am offering DIY kits, factory-assembled PCBs, and a variety of current transformers to use with this project.

Please see https://power-monitor.dalbrecht.tech/ for more information.

---

## How do I install?

> The instructions below are just a quick start. For the full documentation, please see the full documentation site linked below. Please note that this site is still a work in progress as of February 2023.
>
>https://david00.github.io/rpi-power-monitor/


There are several ways to install.

### Flash the custom OS image to your microSD card or USB flash drive/SSD enclosure

See [Software Installation](https://david00.github.io/rpi-power-monitor/docs/general/install-the-software.html#prebuilt-os-image) in the docs.

### Clone the repository

```bash
git clone https://github.com/David00/rpi-power-monitor rpi_power_monitor
```

Then, download the default config file, and start the power monitor:

```bash
cd rpi_power_monitor
python3 -m pip install .
wget https://david00.github.io/rpi-power-monitor/docs/v0.3.0/config.toml -O rpi_power_monitor/config.toml
python3 rpi_power_monitor/power_monitor.py
```

See the [Configuration section](https://david00.github.io/rpi-power-monitor/docs/v0.3.0/configuration.html) in the docs for further information on setting up the power monitor.

### Install python package

```bash

python3 -m pip install git+https://github.com/David00/rpi-power-monitor.git
```

Then, to run, for example:

```python
from rpi_power_monitor import power_monitor

rpm = power_monitor.RPiPowerMonitor()
rpm.run_main()
```



---

## What does it do?

This code accompanies DIY circuitry that supports monitoring of up to 6 current transformers and one AC voltage reading. The individual readings are then used in calculations to provide real data on consumption and generation, including the following key metrics:

* Total home consumption
* Total solar PV generation
* Net home consumption
* Net home generation
* Total current, voltage, power, and power factor values
* Individual current transformer readings
* Harmonics inspection through a built in snapshot/plotting mechanism.

The code takes tens of thousands of samples per second, corrects for phase errors in the measurements, calculates the instantaneous power for the tens of thousands of sampled points, and uses the instantaneous power calculations to determine real power, apparent power, and power factor. This means the project is able to monitor any type of load, including reactive, capacitive, and resisitve loads.

---


## Installation & Documentation

### Please see [the documentation](https://david00.github.io/rpi-power-monitor/docs/general/index.html) for detailed setup instructions.

---

## Contributing

Would you like to help out? Shoot me an email at github@dalbrecht.tech to see what items I currently have pending.

---

### Credits

* [OpenEnergyMonitor](https://openenergymonitor.org) and forum member Robert.Wall for guidance and support

* The `spidev` project on PyPi for providing the interface to read an analog to digital converter

---

### Like my project? Donations are welcome!

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=L6LNLM92MTUY2&currency_code=USD&source=url)

BTC:  1Go1YKgdxAYUjwGM1u3JRXzdyRM938RQ95

###### Last Updated:  April 2023