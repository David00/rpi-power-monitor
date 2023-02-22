---
title: Advanced Usage
parent: v0.3.0-beta
grand_parent: Documentation
layout: default
nav_order: 5
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

If you're using the custom OS image, the power monitor is already setup to run as a service.  This is what enables the power monitor to start automatically on boot, and restart automatically if there are any problems that cause it to crash.

You can check the service status with the following command:

    sudo systemctl status power-monitor.service

The service file is located at `/etc/systemd/system/power-monitor.service`.  


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
python3 power_monitor.py --mode plot [--samples 10000]
    ```
    Output:
    {: .text-delta}
    ```
    
    ```
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

You can use a remote InfluxDB server simply by supplying the server IP or URL, database name, and username/password.  The power monitor will automatically attempt to create the database and setup the retention policies/continuous queries upon the first connection. 

{: .pro-aqua }
Try launching the monitor software with the `--verbose` command-line option to see more detailed output when attempting to setup a remote Influx database.


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

{: .note-cream }
The included [database backup script](./configuration#enabling-automatic-backups) will not work directly on a remote Influx instance, but it can serve as a template to modify and support your remote Influx instance.

## Remote Access

In order to see your power monitor dashboard remotely, you'll have to configure port forwarding on your router.  Essentially, you'll need to forward a port from the public interface on your router, to your Raspberry Pi Power Monitor, port 3000.  If you're not familiar with port forwarding, you'll want to search the internet for a port forwarding guide for your particular router.

Also, most residential internet services are provided as a dynamic public IP address. This means that it will change from time to time.  You can setup a free dynamic DNS service to map your dynamic public IP to a subdomain name under the dynamic DNS service provider's domain.  Essentially, you can pick a free hostname to remember which should always point to your home IP, and you'll no longer have to worry about your dynamic public IP address.

{: .pro-aqua }
Want more than a dynamic DNS name? You can deploy an OpenVPN server at home too to make it easier* and more secure to access devices on your home network.
<br>
\* _(The setup of the VPN server is rather technical, but once it's set up, it's easy to use to securely access your home LAN)_