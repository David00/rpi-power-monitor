---
title: Calibration
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 2
redirect_from: 
  - docs/v0.3.0-beta/calibration  
  - docs/latest/calibration
---

# Calibration
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>


## Items Required

* Multimeter
* [AC current clamp meter (also functions as a voltage multimeter)](https://www.amazon.com/KAIWEETS-Multimeter-Auto-ranging-Temperature-Capacitance/dp/B07Z398YWF?&_encoding=UTF8&tag=rpipowermonit-20&linkCode=ur2&linkId=8d3b4e440b75b31574ccbd7d66b66133&camp=1789&creative=9325")
* SSH access to your Raspberry Pi to update the config file

<small>Some of the links are Amazon Affiliate links, and purchasing the items through these links help support this project.</small>

## Voltage Calibration

{: .note-aqua }
Voltage calibration is required to get an accurate voltage reading from the 9V AC transformer.  It is normal if the voltage over or under reads out of the box.

Using your multimeter, measure the AC voltage at the receptacle where your 9V AC transformer is connected.  Edit `config.toml` and find the `[grid_voltage]` section.

Update the value for `grid_voltage` to match your multimeter's reading.

Next, using your multimeter, measure the output voltage of the 9V AC to AC transformer by inserting one of the probes into the tip of the male barrel connector, and holding another probe on the outer surface of the connector.  

Update the value for `ac_transformer_output_voltage` to match your multimeter's reading.

<details markdown="block">
<summary>Example (click to expand)</summary>
```
[grid_voltage]
grid_voltage = 123.6
ac_transformer_output_voltage = 10.76
frequency = 60
voltage_calibration = 1
```
</details>

Save and close the config file. Then, start the software in terminal mode:

    python3 ~/rpi_power_monitor/rpi_power_monitor/power_monitor.py --mode terminal

Watch the `Voltage` row in the terminal output, and compare the value to your multimeter's reading at the the outlet.  

If the two are not close, calculate the needed calibration factor by dividing the reading from your multimeter by the reading of the power monitor.

<details markdown="block">
<summary>Example (click to expand)</summary>
```
Multimeter Reading: 122.1V

Terminal output:
+-------------+---------+------+-----+-----+-----+-----+
|             |   ct1   | ct2  | ct3 | ct4 | ct5 | ct6 |
+-------------+---------+------+-----+-----+-----+-----+
|    Watts    |  580.4  | 0.0  | 0.0 | 0.0 | 0.0 | 0.0 |
|   Current   |   4.91  | 0.0  | 0.0 | 0.0 | 0.0 | 0.0 |
|     P.F.    |   0.93  |  0   |  0  |  0  |  0  |  0  |
|   Voltage   |  121.4  |      |     |     |     |     |
| Sample Rate |  27.09  | kSPS |     |     |     |     |
+-------------+---------+------+-----+-----+-----+-----+

Calibration Factor = 122.1 / 121.4 = 1.00576  (this value would be applied to the voltage_calibration field in the config file.)
```
</details>


## Amperage Calibration

Prior to calibration, make sure that you have updated your config file with the ratings of each sensor, according to the channel that the sensor is connected to. 

{: .note-aqua }
The sensors from my shop are designed specifically for this project, and the software is pre-calibrated to work with them.  Therefore, the readings should be fairly accurate already, making calibration optional.

{: .danger }
Since the calibration steps outlined below involve working in and around an energized panel, this step should be done by your electrician.

Calibration should be done when the conductors have a reasonable amount of current flowing through them.  Do not calibrate a sensor unless the number of amps in the wire is at least 5% of the sensor's rating.  For example, to calibrate a 100A sensor, you must have at least 5A (5% of 100A) on the wire.

If you want to increase the load on a circuit while calibrating them, halogen work lamps are perfect because they are often high power (500W+), and place a very steady load on the wire, making it easier to compare readings.

Start the software in terminal mode:

    python3 ~/rpi_power_monitor/rpi_power_monitor/power_monitor.py --mode terminal

For each sensor/channel, connect your handheld AC clamp meter around the same wire that the CT is clamped over.  Compare the `Current` output of the power monitor's terminal output to the reading on your AC clamp meter.

If they aren't close, calculate the needed calibration factor by dividing the reading from your clamp meter by the reading of the power monitor.

<details markdown="block">
<summary>Example (click to expand)</summary>
```
AC Clamp Meter reading: 4.65A

Terminal output:
+-------------+---------+------+-----+-----+-----+-----+
|             |   ct1   | ct2  | ct3 | ct4 | ct5 | ct6 |
+-------------+---------+------+-----+-----+-----+-----+
|    Watts    |  580.4  | 0.0  | 0.0 | 0.0 | 0.0 | 0.0 |
|   Current   |   4.91  | 0.0  | 0.0 | 0.0 | 0.0 | 0.0 |
|     P.F.    |   0.93  |  0   |  0  |  0  |  0  |  0  |
|   Voltage   |  122.1  |      |     |     |     |     |
| Sample Rate |  27.09  | kSPS |     |     |     |     |
+-------------+---------+------+-----+-----+-----+-----+

Calibration Factor = 4.65 / 4.91 = 0.947

So, updating config.toml with the calibration factor would look like this:

[current_transformers.channel_1]
name = 'Channel 1'
rating = 20
type = 'consumption'
two_pole = false
enabled = true
calibration = 0.947     # <---- The Calibration Factor is applied here!
watts_cutoff_threshold = 1
```
</details>


After making a change to `config.toml`, save the file, and restart the power monitor in terminal mode.

Repeat these steps for each sensor in use.

After calibration, the software is ready for use! See [Running As A Service](advanced-usage.html#running-as-a-service) in the Advanced Usage section.