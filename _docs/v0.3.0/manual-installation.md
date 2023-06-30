---
title: Manual Software Installation
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 7
redirect_from: 
  - docs/v0.3.0-beta/manual-installation
  - docs/latest/manual-installation
---

# Manual Installation

These instructions assume that you are running 32-bit Raspberry Pi OS Lite.


1. Update and Upgrade 

    ```
    sudo apt update && sudo apt upgrade -y
    ```

2. Install python3, git, pip, and nginx

    ```
    sudo apt install -y python3 python3-pip git nginx
    ```

3. Enable SPI

    ```
    sudo sh -c "echo 'dtparam=spi=on' >> /boot/config.txt"
    ```

4. Modify the permissions of the Nginx webroot so Python can write to it (via your user).

    ```
    sudo chown -R $USER /var/www/html/
    sudo chgrp -R www-data /var/www/html/
    sudo chmod -R 750 /var/www/html/
    ```

5. Update the Nginx configuration to turn file indexing on:

    ```
    sudo nano /etc/nginx/sites-enabled/default
    ```
  

    Find the section that looks like:

    ```
    location / {
            # First attempt to serve request as file, then
            # as directory, then fall back to displaying a 404.
            try_files $uri $uri/ =404;
            }
    ```

    ... and add `autoindex on;` underneath the `try_files` line. The section should look like this when you're done:

    ```
    location / {
              # First attempt to serve request as file, then
              # as directory, then fall back to displaying a 404.
              try_files $uri $uri/ =404;
              autoindex on;
              }
    ```

    Close the text editor with Ctrl-x, then a "Y" to save the file.

7. Remove the default index.html file:

    ```
    rm /var/www/html/index.nginx-debian.html
    ```

  
8. Reboot your Pi:

    ```
    sudo reboot 0
    ```


9. Install Grafana and InfluxDB:

    ```
    sudo wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key
    sudo rm -f /etc/apt/sources.list.d/grafana.list
    echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
    sudo apt update
    sudo apt install -y grafana

    wget -q https://repos.influxdata.com/influxdata-archive_compat.key
    cat influxdata-archive_compat.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
    echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list
    sudo rm -f /etc/apt/sources.list.d/influxdb.list
    sudo apt update
    sudo apt install -y influxdb
    ```

10. Download the source code for this project:

    ```
    git clone --single-branch -b master https://github.com/David00/rpi-power-monitor.git ~/rpi_power_monitor
    ```


11. Navigate into the `rpi_power_monitor` directory and install the Python library dependencies:

    ```
    cd ~/rpi_power_monitor
    pip3 install .
    ```

13. Download the default config file:

    ```
    wget https://david00.github.io/rpi-power-monitor/docs/v0.3.0/config.toml -O ~/rpi_power_monitor/rpi_power_monitor/config.toml
    ```

14. Create the service file:

    ```
    sudo nano /etc/systemd/system/power-monitor.service
    ```

    Paste the following contents in, then save and close the file with `Ctrl-x`, `y`, `enter`.

    {:.note-aqua}
    If you are not using the default `pi` username, make sure you update both the `User=pi` and the `/home/pi/rpi_power_monitor` path with your actual username.

    ```
    [Unit]
    Description=Raspberry Pi Power Monitor
    After=network.target

    [Service]
    Restart=always
    RestartSec=1
    StartLimitInterval=120
    StartLimitBurst=5
    User=pi
    ExecStart=/usr/bin/python3 /home/pi/rpi_power_monitor/rpi_power_monitor/power_monitor.py

    [Install]
    WantedBy=multi-user.target
    ```
    

15. Enable the service file:

    ```
    sudo systemctl enable power-monitor.service
    ```
  
16. Start InfluxDB & Grafana

    ```
    sudo systemctl start influxdb.service grafana-server.service
    ```

17. Start the power monitor manually with `--verbose` to make sure there are no problems:

    ```
    python3 ~/rpi_power_monitor/rpi_power_monitor/power_monitor.py --verbose
    ```

    If this is the very first start, you should see the following output (if it's not the first start, then you should see everything except the continuous query creation messages):

    <details markdown="block">
    <summary>Sample Output (click to expand)</summary>

    ```
    DEBUG : Verbose logs output enabled.
    DEBUG :   ..Checking to see if the power monitor is already running or not...
    DEBUG : Attempting to load config from /home/pi/rpi_power_monitor/rpi_power_monitor/config.toml
    DEBUG : Sampling enabled for 6 channels.
    DEBUG : Identified mains channels: [1, 2]
    DEBUG : Identified 0 production channels: ([])
    DEBUG : Identified 4 consumption channels: ([3, 4, 5, 6])
    DEBUG : Trying to connect to the Influx database at localhost:8086...
    DEBUG : Successfully connected to Influx at localhost:8086
    DEBUG : Created retention policy rp_5min
    DEBUG : Created continuous query: cq_home_power_5m
    DEBUG : Created continuous query: cq_home_energy_5m
    DEBUG : Created continuous query: cq_net_power_5m
    DEBUG : Created continuous query: cq_net_energy_5m
    DEBUG : Created continuous query: cq_solar_power_5m
    DEBUG : Created continuous query: cq_solar_energy_5m
    DEBUG : Created continuous query: cq_ct1_power_5m
    DEBUG : Created continuous query: cq_ct1_energy_5m
    DEBUG : Created continuous query: cq_ct2_power_5m
    DEBUG : Created continuous query: cq_ct2_energy_5m
    DEBUG : Created continuous query: cq_ct3_power_5m
    DEBUG : Created continuous query: cq_ct3_energy_5m
    DEBUG : Created continuous query: cq_ct4_power_5m
    DEBUG : Created continuous query: cq_ct4_energy_5m
    DEBUG : Created continuous query: cq_ct5_power_5m
    DEBUG : Created continuous query: cq_ct5_energy_5m
    DEBUG : Created continuous query: cq_ct6_power_5m
    DEBUG : Created continuous query: cq_ct6_energy_5m
    INFO : ... Starting Raspberry Pi Power Monitor
    INFO : Press Ctrl-c to quit...
    ```
    </details>

16. Stop the power monitor with `Ctrl-c` and proceed to the Configuration documentation.  

    ## [ Go to {{ site.latest-version }} Configuration]( {{site.baseurl}}/docs/{{ site.latest-version }}/configuration ){: .btn .btn-blue }