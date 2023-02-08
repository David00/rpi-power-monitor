---
title: Database Info
parent: v0.3.0-beta
grand_parent: Documentation
layout: default
nav_order: 4
---

# Database Info
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>


## Overview
This project uses InfluxDB (version 1.8.X) to retain measurements.  InfluxDB 1.8 documentation can be found [here](https://docs.influxdata.com/influxdb/v1.8/).

InfluxDB is installed natively in the custom Raspberry Pi OS image as of v0.3.0 (previously, it was ran in a Docker container).  The data are stored in the default path of `/var/lib/influxdb/`.

Visualization of the data is done separately with a dashboard software called Grafana. The Grafana documentation can be found [here](https://grafana.com/docs/grafana/latest/). Grafana develops relatively quickly, so make sure you're looking at the version of the documentation that matches the version you are actually running.

## Structure
If you're familiar with relational SQL tables, Influx is similar in that data are arranged into several "measurements", which are just like SQL tables, with their own columns. In InfluxDB, columns have two types: `fields` and `keys`.  A single record in a measurement is called a `Point`.

{: .reference-cream }
[https://docs.influxdata.com/influxdb/v1.8/concepts/crosswalk/](https://docs.influxdata.com/influxdb/v1.8/concepts/crosswalk/)

One major difference in InfluxDB is on the subject of retention policies. An entire measurement is associated with a retention policy, and to query data from a measurement associated to a specific retention policy, you must specify the retention policy name in addition to the measurement name.  There are examples of this below in the [CLI Access](#cli-access) section.

<details open markdown="block">
<summary>Database Measurement Structure</summary>
{: .text-delta }

| Measurement Name | Retention Policy | Fields             | Tags    | Purpose                                                                         |
|------------------|------------------|--------------------|---------|---------------------------------------------------------------------------------|
| home_load        | autogen          | current, power     |         | The amperage and power your home needs to run.                                  |
| solar            | autogen          | current, power, pf |         | The amperage, power, and power factor of your production sources.               |
| net              | autogen          | current, power     | status  | The amperage and power flowing either to or from the grid.                      |
| raw_cts          | autogen          | current, power, pf | ct      | For each CT, the amperage, power, and power factor as measured by that   CT.    |
| voltages         | autogen          | voltage            | v_input | The calculated grid voltage as measured by the voltage input.                   |
| home_load_5m     | rp_5min          | current, power     |         | The 5 minute average of amperage and power that your home needs to run.         |
| home_energy_5m   | rp_5min          | energy             |         | The 5 minute sum of energy that your home used, in kilowatt-hours.              |
| net_power_5m     | rp_5min          | current, power     |         | The 5 minute average amperage, and power, flowing either to or from the   grid. |
| net_energy_5m    | rp_5min          | energy             |         |                                                                                 |
| solar_power_5m   | rp_5min          | power, current     |         |                                                                                 |
| solar_energy_5m  | rp_5min          | energy             |         |                                                                                 |
| ct1_power_5m     | rp_5min          | power, current     |         |                                                                                 |
| ct1_energy_5m    | rp_5min          | energy             |         |                                                                                 |
| ct2_power_5m     | rp_5min          | power, current     |         |                                                                                 |
| ct2_energy_5m    | rp_5min          | energy             |         |                                                                                 |
| ct3_power_5m     | rp_5min          | power, current     |         |                                                                                 |
| ct3_energy_5m    | rp_5min          | energy             |         |                                                                                 |
| ct4_power_5m     | rp_5min          | power, current     |         |                                                                                 |
| ct4_energy_5m    | rp_5min          | energy             |         |                                                                                 |
| ct5_power_5m     | rp_5min          | power, current     |         |                                                                                 |
| ct5_energy_5m    | rp_5min          | energy             |         |                                                                                 |
| ct6_power_5m     | rp_5min          | power, current     |         |                                                                                 |
| ct6_energy_5m    | rp_5min          | energy             |         |                                                                                 |

</details>

## Data Retention and Continuous Queries
The "high resolution" data - or the data that get calculated roughly once a second - create hundreds of thousands of Points in a single day, across all the different measurements. While this is great to see high resolution data in real time, it's not so great when trying to look at multiple days, weeks, or even years at a time. InfluxDB provides two mechanisms to solve this issue: retention policies, and continuous queries.

{: .reference-cream }
[https://docs.influxdata.com/influxdb/v1.8/guides/downsample_and_retain/](https://docs.influxdata.com/influxdb/v1.8/guides/downsample_and_retain/)

As of v0.3.0, this project uses the following RPs and CQs:

### Retention Policies

| Purpose                                       | Policy Name | Duration |
|-----------------------------------------------|-------------|----------|
| Default - holds the high-res data             | `autogen`   | 30 days  |
| Long-term RP - holds the 5 minute downsamples | `rp_5min`   | forever  |

{: .warning }
Deleting a retention policy will delete all of the data associated to it!

### Continuous Queries

These continuous queries will automatically down sample the high resolution data into 5 minute intervals. The results of the downsampling get stored in a new measurement that is associated to the `rp_5min` retention policy.  

{: .note-aqua }
To look at the data from the downsampled results, you must specify the retention policy name in the query! Example:
`SELECT SUM(energy) from rp_5min.home_energy_5m where time >= now() - 1d;`


| Purpose                       | CQ Name              | Measurement Name  | Results go into `rp_name` .   `measurement_name`        |
|-------------------------------|----------------------|-------------------|---------------------------------------------------------|
| Home Power - Average          | `cq_home_power_5m`   | `home_load_5m`    | `rp_5min.home_load_5m`                                  |
| Home Energy - Sum             | `cq_home_energy_5m`  | `home_energy_5m`  | `rp_5min.home_energy_5m`                                |
| Net Power - Average           | `cq_net_power_5m`    | `net_power_5m`    | `rp_5min.net_power_5m`                                  |
| Net Energy - Sum              | `cq_net_energy_5m`   | `net_energy_5m`   | `rp_5min.net_energy_5m`                                 |
| Solar Power - Average         | `cq_solar_power_5m`  | `solar_power_5m`  | `rp_5min.solar_power_5m`                                |
| Solar Energy - Sum            | `cq_solar_energy_5m` | `solar_energy_5m` | `rp_5min.solar_energy_5m`                               |
| Individual CT Power - Average | `cq_ct#_power_5m`    | `ct#_power_5m`    | `rp_5min.ct#_power_5m` (where # is the channel number)  |
| Individual CT Energy - Sum    | `cq_ct#_energy_5m`   | `ct#_energy_5m`   | `rp_5min.ct#_energy_5m` (where # is the channel number) |


## CLI Access 
To get into the InfluxDB command line, simply type `influx` at your terminal prompt.

{: .pro-aqua }
Use the following command and flags to go straight into the power monitor database, with human readable timestamps:
`influx -precision rfc3339 -database power_monitor`

{: .reference-cream }
[https://docs.influxdata.com/influxdb/v1.8/query_language/explore-data/](https://docs.influxdata.com/influxdb/v1.8/query_language/explore-data/)



## Backups
InfluxDB includes a built in command-line backup mechanism.  I have incorporated this functionality into a backup script included with this project, which automatically backs up your Influx data, app configuration, and stores it on an external USB flash drive. See [Enabling Automatic Backups](configuration#enabling-automatic-backups) for more info.

For the native InfluxDB backup mechanism, see the official docs below:

{: .reference-cream }
[https://docs.influxdata.com/influxdb/v1.8/tools/influxd/backup/](https://docs.influxdata.com/influxdb/v1.8/tools/influxd/backup/)