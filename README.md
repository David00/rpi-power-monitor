# Raspberry Pi Power Monitor

The Raspberry Pi Power Monitor is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time (<0.5 second intervals), including accurate consumption, generation, and net-production. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

This project is derived from and inspired by the resources located at https://learn.openenergymonitor.org. 


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

        sudo usermod -aG docker pi
        

5. Enable the SPI interface on the Pi

        sudo raspi-config
        
    Use the arrow keys and the Enter key to:
    * Select "5 Interfacing Options"
    * Select "P4 SPI"
    * Enable the SPI interface
    * Press Tab twice to move the selector to Finish
        
6. Modify the permissions of the webroot so that Python can write to it. If you're not using the `pi` username, be sure to change it before executing the commands below:

        sudo chown -R pi /var/www/html/
        sudo chgrp -R www-data /var/www/html/
        sudo chmod -R 750 /var/www/html/

7. Update the Nginx configuration to turn file indexing on, and remove the default Nginx index file:
        
        sudo nano /etc/nginx/sites-enabled/default
        
    Find the section that looks like:

        location / {
                 # First attempt to serve request as file, then
                 # as directory, then fall back to displaying a 404.
                 try_files $uri $uri/ =404;
                 }
                 
    ... and add `autoindex on;` underneath the `try_files` line. The block should look like this:
    
        location / {
                 # First attempt to serve request as file, then
                 # as directory, then fall back to displaying a 404.
                 try_files $uri $uri/ =404;
                 autoindex on;
                 }
                 
    Close your text editor with Ctrl-x, then a "Y" to save the file.  Then, remove the default index.html file:
    
        rm /var/www/html/index.nginx-debian.html
        
        
8. Reboot your Pi:

        sudo reboot 0

7. Download and run the Grafana and InfluxDB Docker images
        
        docker run -d --restart always --name grafana -p 3000:3000 grafana/grafana
        docker run -d --restart always --name influx -p 8086:8086 -v /opt/influxdb:/var/lib/influxdb influxdb

8. Run `docker ps` and confirm that the two docker containers are running. Here is what the output should look like. Your container IDs will be different, but the rest should be the same.

        pi@raspberrypi:~ $ docker ps
        CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                               NAMES
        013caaf13240        influxdb            "/entrypoint.sh infl…"   19 seconds ago      Up 16 seconds       0.0.0.0:8086->8086/tcp              influx
        8e763709b515        grafana/grafana     "/run.sh"                3 minutes ago       Up 3 minutes        3000/tcp, 0.0.0.0:3000->3000/tcp   grafana


    >Note: If you get a permission error when executing the `docker ps` command, make sure you entered the correct username in step #4 and that you have either logged out and back in, or simply rebooted your Pi.

9. Download the source code for this project

        git clone --single-branch -b master https://github.com/David00/rpi-power-monitor.git


10. Navigate into the `rpi-power-monitor` directory and install the Python library dependencies.

        cd rpi-power-monitor
        pip3 install -r requirements.txt 

### Next Steps

Head to the [project Wiki](https://github.com/David00/rpi-power-monitor/wiki) to get started on the rest of the setup process.


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

###### Last Updated:  June 26, 2020
