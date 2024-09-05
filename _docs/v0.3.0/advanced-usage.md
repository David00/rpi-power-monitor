---
title: Advanced Usage
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 5
redirect_from: 
  - docs/v0.3.0-beta/advanced-usage
  - docs/latest/advanced-usage
---

# Advanced Usage
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>

## Running as a Service

If you're using the custom OS image, a service file already exists, but you'll need to enable it. The service file is what enables the power monitor to start automatically on boot and restart automatically if there are any problems that cause it to crash.  Enable the service with the following command:

```
sudo systemctl enable power-monitor.service
```

You can check the service status with the following command:

    sudo systemctl status power-monitor.service

In the custom OS release, the service file is located at `/etc/systemd/system/power-monitor.service`.

<details open markdown="block">
<summary id="service-file-contents">Here are the contents of the default service file:</summary>
```
[Unit]
Description=Raspberry Pi Power Monitor
After=network.target
Wants=influxdb.service

[Service]
Restart=always
RestartSec=2
StartLimitInterval=0
StartLimitBurst=5
User=pi
ExecStart=/usr/bin/python3 /home/pi/rpi_power_monitor/rpi_power_monitor/power_monitor.py

[Install]
WantedBy=multi-user.target
```
</details>

{: .note-aqua }
If you are not using the default `pi` user, you'll need to edit the service file and change the `User=` and `ExecStart=` lines with the correct username and path to the power monitor project.

### Creating the Service File

1. Remove the file if it exists:

    ```
    sudo rm /etc/systemd/system/power-monitor.service
    ```

2. Create the file, paste <a href="#service-file-contents">the contents</a> from above into this file:

    ```
    sudo nano /etc/systemd/system/power-monitor.service
    ```

3. Save and close the file with `Ctrl-x`, then `y`, then `Enter`

4. Tell systemctl to refresh the service files and enable the power monitor service file:

    ```
    sudo systemctl daemon-reload && sudo systemctl enable power-monitor.service
    ```


### Controlling the Power Monitor Background Service

All commands are with the systemd control command: `systemctl`. This command takes various arguments like `status`, `start`, `stop`, and more.

1. View the current status:
    
    ```
    sudo systemctl status power-monitor.service
    ```

2. Start the power monitor in the background:

    ```
    sudo systemctl start power-monitor.service
    ```

3. Stop the power monitor:

    ```
    sudo systemctl stop power-monitor.service
    ```

4. Restart the power monitor:

    ```
    sudo systemctl restart power-monitor.service
    ```

## Command Line Interface

Here you'll find an overview of the different command line options.  You can also run `python3 ~/rpi_power_monitor/rpi_power_monitor/power_monitor.py --help` to see the available command line options.

### `--mode`
{: .fs-6 .no_toc }

The power monitor supports the following modes of operation:

* `main` : The default mode. (You do not need to specify `--mode main` to start the power monitor in this mode).
* `terminal` : Prints a table containing the measurements from all channels.  

    {: .fh-default }
    <details markdown="block">    
    <summary>Click to expand the example output from <code class="language-plaintext highlighter-rouge">terminal</code> mode</summary>

    How to use:
    {: .text-delta}
    ```
python3 power_monitor.py --mode terminal
    ```
    Output
    {: .text-delta}

    ```
    INFO : ... Starting Raspberry Pi Power Monitor
    INFO : Press Ctrl-c to quit...
    INFO :
    +-------------+---------+----------+----------+--------+--------+--------+
    |             |   ct1   |   ct2    |   ct3    |  ct4   |  ct5   |  ct6   |
    +-------------+---------+----------+----------+--------+--------+--------+
    |    Watts    |  839.8  | 1079.235 | 1552.306 | -1.313 | -0.767 | -0.269 |
    |   Current   |   7.18  |  9.701   |  13.179  | 0.202  | 0.193  | 0.197  |
    |     P.F.    |  0.947  |  0.901   |  0.954   | -0.053 | -0.032 | -0.011 |
    |   Voltage   | 123.486 |          |          |        |        |        |
    | Sample Rate |  24.61  |   kSPS   |          |        |        |        |
    +-------------+---------+----------+----------+--------+--------+--------+
    ```
    </details>

* `plot` : Captures, by default, 1000 samples from each channel, and plots them to an interactive HTML plot.  The power monitor terminates after generating the plot.
Specify the number of samples (per channel) with the optional argument `--samples N`.

    <details markdown="block">    
    <summary>Click to expand the sample usage for the <code class="language-plaintext highlighter-rouge">plot</code> mode.</summary>

    How to use:
    {: .text-delta}
    ```
python3 power_monitor.py --mode plot --samples 1000
    ```
    Output:
    {: .text-delta}
    ```
    INFO : Plot created! Visit http://192.168.10.219/Generated-Plot_04-02-23_001055.html to view the chart. Or, simply visit http://192.168.10.219 to view all the charts created using '--plot' mode.
    ```
    You can view the plot by accessing the link that your terminal shows from a web browser on another device on the same network as the Raspberry Pi.
    </details>



### `--config`
{: .fs-6 .no_toc }
Provide the path to your `config.toml` configuration file. The power monitor, by default, looks in the same directory as the `power_monitor.py` file, which is usually `/home/pi/rpi_power_monitor/rpi_power_monitor/`.

How to use:
{: .text-delta}
```
python3 power_monitor.py --config /path/to/config.toml
```

### `-v, --verbose`
{: .fs-6 .no_toc }
Enables debug logging to the console. This provides more detailed information about the startup process, including loading and parsing the configuration file and database connectivity.

How to use:
{: .text-delta}
```
python3 power_monitor.py --verbose
```

### `-V, --version`
{: .fs-6 .no_toc }
Prints the power monitor software version to the console.

How to use:
{: .text-delta}
```
python3 power_monitor.py --version
```


## Integrations (Home Assistant, etc.)

TBD

## Using A Remote InfluxDB Server

You can use a remote InfluxDB server simply by supplying the server IP or URL, database name, and username/password.  The power monitor will automatically attempt to create the database and setup the retention policies/continuous queries upon the first connection. You'll also need to [configure Grafana](#add-remote-datasource-to-grafana) to point to the new remote InfluxDB server. 

You'll need to [install InfluxDB version 1.8.X ](https://docs.influxdata.com/influxdb/v1.8/introduction/install/#installing-influxdb-oss) on your remote machine, which could be another Raspberry Pi, a cloud VPS, or your desktop computer. In any case, it should be a machine that has reliable power and network connectivity.

{: .pro-aqua }
Try launching the monitor software with the `--verbose` command-line option to see more detailed output when attempting to setup a remote Influx database.

Simply edit your power monitor's `config.toml` file with the host, port, and optional username/password (if configured).

<details markdown="block">
<summary>Sample Configuration (click to expand)</summary>

```
[database]
host = "192.168.0.101"
port = 8086
username = "root"
password = "password"
database_name = "power_monitor"
```
</details>

### Add Remote Datasource to Grafana
When using a remote datasource, you also need to tell Grafana about the remote source. Login to your Grafana instance as an admin user and follow the steps below to make the change.

1. Go to Configuration -> Data Sources
2. Select "Add Data Source"
3. Search for, and select, InfluxDB
4. Fill out the fields for the new datasource.
    * Name
    * URL (in the format http://192.168.1.123:8086)
    * Database (the same as `database_name` entered above)
    * User and password if you've setup the InfluxDB server with a username and password

5. Click Save & Test. You should see a green checkmark with a message "Datasource is working".  Make sure you have started the power monitor at least one time against the remote InfluxDB server before this step (the power monitor will create the database on the remote server upon startup).
6. Lastly, you'll need to update each panel in the dashboard to retrieve its data from the new datasource.  Click on each panel's title, select edit, and change the "Data Source" dropdown (directly above the query builder section) to the name of the new datasource you entered in step 4.
7. Don't forget to save the dashboard!


{: .note-cream }
The included [database backup script](./configuration#enabling-automatic-backups) will not work directly on a remote Influx instance, but it can serve as a template to modify and support your remote Influx instance.



## Remote Access

In order to see your power monitor dashboard remotely, you'll have to configure port forwarding on your router.  Essentially, you'll need to forward a port from the public interface on your router, to your Raspberry Pi Power Monitor, port 3000.  If you're not familiar with port forwarding, you'll want to search the internet for a port forwarding guide for your particular router.

Also, most residential internet services are provided as a dynamic public IP address. This means that it will change from time to time.  You can setup a free dynamic DNS service to map your dynamic public IP to a subdomain name under the dynamic DNS service provider's domain.  Essentially, you can pick a free hostname to remember which should always point to your home IP, and you'll no longer have to worry about your dynamic public IP address.

{: .pro-aqua }
Want more than a dynamic DNS name? You can deploy an OpenVPN server at home too to make it easier* and more secure to access devices on your home network.
<br>
\* _(The setup of the VPN server is rather technical, but once it's set up, it's easy to use to securely access your home LAN)_