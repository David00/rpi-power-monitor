---
title: Configuration
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 1
---

# Configuration

The first half of this page is a step-by-step guide to setup your power monitor using the included power-monitor file.  See below for the [Configuration Reference Manual](#configuration-reference-manual), which contains information about all of the available configuration options.

{: .note-cream }
This configuration process is new as of version 0.3.0. Previous versions relied on a different (and less robust) configuration.


### Configuring your Power Monitor

The configuration file is located at `~/rpi-power-monitor/rpi_power_monitor/config.toml`.

Follow the steps below to setup your power monitor.

{: .note-cream }
There are configuration options that will require a multimeter and AC clamp meter. Those steps are covered separately in the Calibration section of the docs.

You'll need to open the config file with your favorite text editor to update it.  I'll use `nano` for this walkthrough:

    nano ~/rpi-power-monitor/rpi_power_monitor/config.toml


Find the `[grid_voltage]` section.  Make sure `frequency` is set correctly for your region. It should be either 50 or 60, corresponding to 60Hz grids or 50Hz grids. (**Hint:** US/Canada/Mexico should be 60Hz - _mostly_ everywhere else is 50Hz)

Skip down to the `[current_transformers.channel_#]` sections.  Each CT channel has its own section containing its own settings.  The only things you'll need to change here (for now) are:

* `name`: the name of the circuit
* `rating`: the amperage rating of the **sensor** used on this channel
* `type`: either `production`, `consumption`, or `mains`. See the configuration reference manual for more info.

{: .example-cream }
In the [Planning section](/docs/general/create-your-plan#planning), I created a sample list of requirements. Remember, those requirements were based on the rating of the **breaker**, and the config file needs the rating of the **sensor**.
#### Configuration Example: 
[expand]
```
[current_transformers.channel_1]
name = 'Main #1'
rating = 200
type = 'mains'
two_pole = false
enabled = true
calibration = 1.0
watts_cutoff_threshold = 0

[current_transformers.channel_2]
name = 'Main #2'
rating = 200
type = 'mains'
two_pole = false
enabled = true
calibration = 1.0
watts_cutoff_threshold = 0

[current_transformers.channel_3]
name = 'Solar'
rating = 100
type = 'production'
two_pole = true
enabled = true
calibration = 1.0
watts_cutoff_threshold = 0

[current_transformers.channel_4]
name = 'AC Unit'
rating = 30
type = 'consumption'
two_pole = true
enabled = true
calibration = 1.0
watts_cutoff_threshold = 0

[current_transformers.channel_5]
name = 'Master Bedroom'
rating = 20
type = 'consumption'
two_pole = false
enabled = true
calibration = 1.0
watts_cutoff_threshold = 0

[current_transformers.channel_6]
name = 'EV Charger'
rating = 60
type = 'consumption'
two_pole = true
enabled = true
calibration = 1.0
watts_cutoff_threshold = 0
```
[/expand]


> When finished making changes, press `Ctrl-x`, then `y` to save and close the config file.

---


# Configuration Reference Manual

See below for detailed information on each of the settings in the configuration file.

#### [general]

<h3 id="name" class='config-value'><a class="anchor-heading" href="#name" aria-labelledby="name"></a>name</h3>

Represents the name of your power monitor. This value will be used to tag all entries in InfluxDB.  This is useful if you have a centralized InfluDB server and multiple power monitors all logging to the same server, because it allows you to distinguish which data points are coming from which power monitor.

#### [data_retention]



#### [database]

<h3 id="host" class='config-value'><a class="anchor-heading" href="#host" aria-labelledby="host"></a>host</h3>

The IPv4 address or URL of your InfluxDB server.  See [Advanced Usage (TBD!!!!!!!!!!)[] for details on setting up a remote InfluxDB instance.

> Default: `localhost`

<h3 id="port" class='config-value'><a class="anchor-heading" href="#port" aria-labelledby="port"></a>port</h3>

The port number for your InfluxDB server. 

> Default: 8086

<h3 id="username" class='config-value'><a class="anchor-heading" href="#username" aria-labelledby="username"></a>username</h3>

The username for your InfluxDB instance. By default, InfluxDB (versions <=1.8.x) do not have default credentials.  If you have not specifically setup credentials, you can leave this as-is.

<h3 id="password" class='config-value'><a class="anchor-heading" href="#password" aria-labelledby="password"></a>password</h3>

The password for your InfluxDB instance. By default, InfluxDB (versions <=1.8.x) do not have default credentials.  If you have not specifically setup credentials, you can leave this as-is.


<h3 id="database_name" class='config-value'><a class="anchor-heading" href="#database_name" aria-labelledby="database_name"></a>database_name</h3>

The name of your InfluxDB database.

> Default: `power_monitor`

#### [grid_voltage]

<h3 id="grid_voltage" class='config-value'><a class="anchor-heading" href="#grid_voltage" aria-labelledby="grid_voltage"></a>grid_voltage</h3>

The grid voltage, as measured by your multimeter at the outlet.

<h3 id="ac_transformer_output_voltage" class='config-value'><a class="anchor-heading" href="#ac_transformer_output_voltage" aria-labelledby="ac_transformer_output_voltage"></a>ac_transformer_output_voltage</h3>

The output voltage of your AC transformer, as measured by your multimeter.

{: .note-aqua }
Do not use the label on your AC transformer - you must take a measurement with a multimeter. This is because transformers often put out higher voltages at virtually no load.


#### [current_transformers.channel_#]