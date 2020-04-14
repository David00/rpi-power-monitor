# Raspberry Pi Power Monitor

The Raspberry Pi Power Monitor is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time (<0.5 second intervals), including consumption, generation, and net-production. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

This project is derived from the resources located at https://learn.openenergymonitor.org. 



---

## What does it do?

This code accompanies DIY circuitry (see the references above) that supports monitoring of up to 6 current transformers and one AC voltage reading. The individual readings are then used in calculations to provide real data on consumption and generation, including the following key metrics:

* Total home consumption
* Total solar PV generation
* Net home consumption
* Net home generation
* Total current, voltage, power, and power factor values
* Individual current transformer readings

---

## Installation

These steps are for the Raspbian (Debian-based) operating system. I highly recommend using the "lite" version of Raspbian to avoid wasting resources on a GUI.  Also, I have only tested this code on a Raspberry Pi 3b+. I would not recommend using an older Raspberry Pi.

In summary, the following steps will:

* Update and upgrade your Pi
* Install Python 3.7 & pip
* Install Git
* Install Nginx (optional, but recommended for viewing raw data - more on this in the project Wiki)
* Install Docker
* Download the InfluxDB and Grafana docker images
* Download the source code for this project
* Install the Python dependencies for the source code

You should assign a static IP address to your Pi and issue the following commands over an SSH connection. There are countless guides on the internet to do this... [here](https://pimylifeup.com/raspberry-pi-static-ip-address/) is one. 


1. Update and upgrade your system:

        sudo apt-get update && sudo apt-get upgrade

2. Install Python 3.7, Git, Pip, and Nginx:

        sudo apt-get install python3.7 python3-pip git nginx

3. Install Docker

        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh

4. Add the default Pi user to the docker group. If you are using a different username, replace Pi with your username:

        sudo usermod -aG docker Pi

5. Reboot your Pi:

        sudo reboot 0

6. Download the source code for this project

        git clone https://github.com/David00/rpi-power-monitor.git


7. Navigate into the `rpi-power-monitor` directory and install the Python library dependencies.

        cd rpi-power-monitor
        pip3 install -r requirements.txt 

### Next Steps

Head to the project Wiki's [Quickstart section](https://github.com/David00/rpi-power-monitor/wiki#quick-start--table-of-contents) to get started on the rest of the setup process.


---

### Credits

* [OpenEnergyMonitor](https://openenergymonitor.org) and forum member Robert.Wall for guidance and support

* The `spidev` project on PyPi for providing the interface to read an analog to digital converter


---


###### Last Updated:  April 13, 2020
