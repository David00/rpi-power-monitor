---
title: Configuration
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 1
redirect_from: 
  - docs/v0.3.0-beta/configuration
  - docs/latest/configuration
---

# Configuration
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>

## Configuring your Power Monitor

{: .note-cream }
This configuration process is new as of version 0.3.0. Previous versions relied on a different (and less robust) configuration.

The configuration file is located at `~/rpi_power_monitor/rpi_power_monitor/config.toml`.  

<details markdown="block">
<summary>Don't see it there?  Click for download options:</summary>

1. Download directly to your Pi via the command line:

    ```
    wget https://david00.github.io/rpi-power-monitor/docs/v0.3.0/config.toml -O ~/rpi_power_monitor/rpi_power_monitor/config.toml
    ```

2. Download to your computer:

    [Download](https://david00.github.io/rpi-power-monitor/docs/v0.3.0/config.toml){: .btn .btn-blue }

</details>


Follow the steps below to setup your power monitor.

{: .note-cream }
There are configuration options that will require a multimeter and AC clamp meter. Those steps are covered separately in the Calibration section of the docs.

You'll need to open the config file with your favorite text editor to update it.  I'll use `nano` for this walkthrough:

    nano ~/rpi_power_monitor/rpi_power_monitor/config.toml

### Setting Grid Voltage Parameters

Find the `[grid_voltage]` section.  Make sure `frequency` is set correctly for your region. It should be either 50 or 60, corresponding to 60Hz grids or 50Hz grids. (**Hint:** US/Canada/Mexico should be 60Hz - _mostly_ everywhere else is 50Hz)

### Setting Current Transformer (CT) Sensor Details
Skip down to the `[current_transformers.channel_#]` sections.  Each CT channel has its own section containing its own settings.  The only things you'll need to change here (for now) are:

* `name`: the name of the circuit
* `rating`: the amperage rating of the **sensor** used on this channel
* `type`: either `production`, `consumption`, or `mains`. See [this part](configuration#type) of the configuration reference manual for details about these options.

{: .example-cream }
In the [Planning section]({{site.baseurl}}/docs/general/create-your-plan#planning), I created a sample list of requirements. Remember, those requirements were based on the rating of the **breaker**, and the config file needs the rating of the **sensor**.

<details markdown="block">
<summary>Configuration Example (click to expand):</summary>
```

[current_transformers.channel_1]
name = 'Main #1'
rating = 200
type = 'mains'
two_pole = false
enabled = true
calibration = 1.0
amps_cutoff_threshold = 0
watts_cutoff_threshold = 0
reversed = false
phase_angle = 0

[current_transformers.channel_2]
name = 'Main #2'
rating = 200
type = 'mains'
two_pole = false
enabled = true
calibration = 1.0
amps_cutoff_threshold = 0
watts_cutoff_threshold = 0
reversed = false
phase_angle = 0

[current_transformers.channel_3]
name = 'Solar'
rating = 100
type = 'production'
two_pole = true
enabled = true
calibration = 1.0
amps_cutoff_threshold = 0
watts_cutoff_threshold = 0
reversed = false
phase_angle = 0

[current_transformers.channel_4]
name = 'AC Unit'
rating = 30
type = 'consumption'
two_pole = true
enabled = true
calibration = 1.0
amps_cutoff_threshold = 0
watts_cutoff_threshold = 0
reversed = false
phase_angle = 0

[current_transformers.channel_5]
name = 'Master Bedroom'
rating = 20
type = 'consumption'
two_pole = false
enabled = true
calibration = 1.0
amps_cutoff_threshold = 0
watts_cutoff_threshold = 0
reversed = false
phase_angle = 0

[current_transformers.channel_6]
name = 'EV Charger'
rating = 60
type = 'consumption'
two_pole = true
enabled = true
calibration = 1.0
amps_cutoff_threshold = 0
watts_cutoff_threshold = 0
reversed = false
phase_angle = 0
```
</details>


> When finished making changes, press `Ctrl-x`, then `y` to save and close the config file.


### Enabling Automatic Backups

An automatic backup script is included with this project, as of v0.3.0. 

> The script is located at `~/rpi_power_monitor/rpi_power_monitor/backup.py`

It will backup your configuration and all of the power monitor data to an external USB flash drive. To use it, follow the steps below to update the power monitor config with the USB device name, and enable the scheduled cron job.

{: .note-aqua }
When the backup runs, it will stop the power monitor service. This is to reduce the demand on the database and help the backup complete as quickly as possible. Once the backup is done, the power monitor service will be restarted automatically.

Connect your USB flash drive to one of the Pi's USB ports, and run the following command:

    sudo fdisk -l | grep "/dev/sd*"

Find the partition number for your flash drive, which should look like `/dev/sda1` or `/dev/sdb1`.

In `config.toml`, set `backup_device` equal to what you found above for your device name and partition number:

<details markdown="block">
<summary>Example (click to expand):</summary>
    [backups]
    backup_device = '/dev/sda1'
</details>

Now that the backup script knows where to put your backups, enable the job from root's crontab:

    sudo crontab -e -u root

If prompted, select option 1 to use Nano.  Then, uncomment (remove the `#` at the front) the existing line:

    0 0 * * 0 python3 /home/pi/rpi_power_monitor/rpi_power_monitor/backup.py

Save and close the file with `Ctrl-x`, then `y`.

The backup will run every Sunday at midnight.  Feel free to adjust the cron scheduling parameters if you want the backup to run more or less often.

{: .note-aqua }
To start the backup script manually, use the following command:
<br>
`sudo python3 /home/pi/rpi_power_monitor/rpi_power_monitor/backup.py`


{: .note-aqua }
Done with the initial configuration? Proceed to [Calibration](./calibration).

---

# Configuration Reference Manual

See below for detailed information on each of the settings in the configuration file.

## [general]

<h3 id="name" class='config-value'><a class="anchor-heading" href="#name" aria-labelledby="name"></a>name</h3>

Represents the name of your power monitor. This value will be used to tag all entries in InfluxDB.  This is useful if you have a centralized InfluDB server and multiple power monitors all logging to the same server, because it allows you to distinguish which data points are coming from which power monitor.

<h3 id="three_phase_mode" class='config-value'><a class="anchor-heading" href="#three_phase_mode" aria-labelledby="three_phase_mode"></a>three_phase_mode</h3>

When set to `true`, this setting will use the three-phase variant of the power calculation routine. Leave this setting to it's default value of `false` unless you have a three-phase system and have completed the 3-phase setup.

> Default: `false`

## [data_retention]

TBD

## [database]

<h3 id="host" class='config-value'><a class="anchor-heading" href="#host" aria-labelledby="host"></a>host</h3>

The IPv4 address or URL of your InfluxDB server.  See [Advanced Usage](advanced-usage) for details on setting up a remote InfluxDB instance.

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

## [grid_voltage]

<h3 id="grid_voltage" class='config-value'><a class="anchor-heading" href="#grid_voltage" aria-labelledby="grid_voltage"></a>grid_voltage</h3>

The grid voltage, as measured by your multimeter at the outlet.

<h3 id="ac_transformer_output_voltage" class='config-value'><a class="anchor-heading" href="#ac_transformer_output_voltage" aria-labelledby="ac_transformer_output_voltage"></a>ac_transformer_output_voltage</h3>

The output voltage of your AC transformer, as measured by your multimeter.

{: .note-aqua }
Do not use the label on your AC transformer - you must take a measurement with a multimeter. This is because transformers often put out higher voltages when there's no load on them.


## [current_transformers.channel_#]

<h3 id="name" class='config-value'><a class="anchor-heading" href="#name" aria-labelledby="name"></a>name</h3>

The circuit name, or appliance name, that the channel is measuring.

<h3 id="rating" class='config-value'><a class="anchor-heading" href="#rating" aria-labelledby="rating"></a>rating</h3>

The rating of the **sensor** used for this channel, in Amperes. This should be a numerical value - do not include the "A".

<h3 id="type" class='config-value'><a class="anchor-heading" href="#type" aria-labelledby="type"></a>type</h3>

The type description of the power being monitored. It must be one of the following:

* `production` : The sensor is monitoring the AC output of a solar inverter, generator, wind turbine, or other source of power production.
* `consumption` : The sensor is monitoring a circuit or appliance that consumes power.  
* `mains` : The sensor is monitoring one of (or the) panel's main feed.

{: .note-aqua }
These types are used in the software to calculate your net power. It is important to use the proper type description for each channel when setting up whole home monitoring.

<h3 id="two_pole" class='config-value'><a class="anchor-heading" href="#two_pole" aria-labelledby="two_pole"></a>two_pole</h3>

If the sensor is measuring a single leg of a two-pole breaker, set this to `true`. Otherwise, leave it as `false`.  By setting this to true, the measurements from the sensor will be doubled.  If you are using a sensor on each leg of a two-pole circuit, leave both values as false since you're directly measuring both legs (and don't need to double the measurement).

> Default: false

<h3 id="enabled" class='config-value'><a class="anchor-heading" href="#enabled" aria-labelledby="enabled"></a>enabled</h3>

Enables or disables the channel. Disabling a channel will speed up your per-channel sampling rate.

> Default: true

<h3 id="calibration" class='config-value'><a class="anchor-heading" href="#calibration" aria-labelledby="calibration"></a>calibration</h3>

A constant value used to align the amperage measurement from a sensor to your calibration source. For example, if your handheld AC clamp meter is measuring 5.7A, and the sensor is measuring a higher value of 6.5A, the sensor value needs to be reduced.  To get the value, divide the correct value (5.7) by what the power monitor is reporting (6.5). So, `5.7 / 6.5 = 0.8769`.  So, you'd use `0.8769` as the value for calibration for this channel.

> Default: 1.0

<h3 id="amps_cutoff_threshold" class='config-value'><a class="anchor-heading" href="#amps_cutoff_threshold" aria-labelledby="amps_cutoff_threshold"></a>amps_cutoff_threshold</h3>

This is a software-based filter to help remove very low power noise.  The value you enter here will be the absolute minimum value the power monitor will require in order to save the calculation to the database.  For example, if you set this to `0.2`, the power monitor will ignore all readings for this channel until they are above 0.2 Amps.  When data falls below this threshold, the power monitor will hardcode the reading to 0 for power, current, and power factor (PF).

The power monitor will ignore the sign of the power measurement (aka, the absolute value) when comparing the measurement to the cutoff threshold. For example, with a `amps_cutoff_threshold` of 0.2, a measurement of -0.3 Amps will not be ignored, but a measurement of -0.15 will be ignored.

Leave the value at 0 to disable this feature.

> Default: 0


<h3 id="watts_cutoff_threshold" class='config-value'><a class="anchor-heading" href="#watts_cutoff_threshold" aria-labelledby="watts_cutoff_threshold"></a>watts_cutoff_threshold</h3>

> DEPRECATED AS OF v0.3.2 - will be removed in a future release. Please update your configuration to use the `amps_cutoff_threshold` above instead.

This is a software-based filter to help remove very low power noise.  The value you enter here will be the absolute minimum value the power monitor will require in order to save the calculation to the database.  For example, if you set this to `2`, the power monitor will ignore all readings for this channel until they are above 2 Watts.  When data falls below this threshold, the power monitor will hardcode the reading to 0 for power, current, and power factor (PF).

The power monitor will ignore the sign of the power measurement (aka, the absolute value) when comparing the measurement to the cutoff threshold. So, with a `watts_cutoff_threshold` of 1.0, a measurement of -100 Watts will not be ignored, but a measurement of -0.25W will be ignored.

Leave the value at 0 to disable this feature.

> Default: 0

<h3 id="reversed" class='config-value'><a class="anchor-heading" href="#reversed" aria-labelledby="reversed"></a>reversed</h3>

When set to `true`, this setting will negate the readings for this channel. If the channel is reading negative when it is supposed to be reading positive, or vice versa, set this to `true`.

> Default: `false`

<h3 id="phase_angle" class='config-value'><a class="anchor-heading" href="#phase_angle" aria-labelledby="phase_angle"></a>phase_angle</h3>

*For 3-phase-mode only.*

This setting holds the measured default phase angle from the perspective of the power monitor, and is used in calculations when <a href="#three_phase_mode">`three_phase_mode`</a> is enabled.

> Default: `0`

## [backups]

<h3 id="backup_device" class='config-value'><a class="anchor-heading" href="#backup_device" aria-labelledby="backup_device"></a>backup_device</h3>

This should be the full path to the partition on your removable device.  To find the partition, connect your already-formatted USB drive, then run the following command:

    sudo fdisk -l | grep "/dev/sd*"

<details open markdown="block">
<summary>Sample Output:</summary>
```
Disk /dev/sda: 28.64 GiB, 30752000000 bytes, 60062500 sectors
/dev/sda1  *     2048 60061695 60059648 28.6G  c W95 FAT32 (LBA)
```
</details>

With the sample output above, the value for `backup_device` should be `/dev/sda1`.

<h3 id="folder_name" class='config-value'><a class="anchor-heading" href="#folder_name" aria-labelledby="folder_name"></a>folder_name</h3>
The name of the folder that will be created on your USB drive to hold the backups.

<h3 id="mount_path" class='config-value'><a class="anchor-heading" href="#mount_path" aria-labelledby="mount_path"></a>mount_path</h3>
The path that your USB drive will be mounted to on your local filesystem. You won't need to change this unless you are already using `/media/backups` on your Raspberry Pi (and even then, you still shouldn't have to).

<h3 id="backup_count" class='config-value'><a class="anchor-heading" href="#backup_count" aria-labelledby="backup_count"></a>backup_count</h3>
The number of backups to keep on the flash drive. The backup utility will automatically remove old backups when the total count of backup files on your USB drive exceeds this limit.