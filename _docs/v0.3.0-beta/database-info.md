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

Visualization of the data is done separately with a dashboard software called Grafana. The Grafana documentation can be found [here](https://grafana.com/docs/grafana/latest/). Grafana goes through development changes rather quickly, so make sure you're looking at the version of the documentation that matches the version you are actually running.

## Structure
If you're familiar with relational SQL tables, Influx is similar in that data are arranged into several "measurements", which are just like SQL tables, with their own columns. In InfluxDB, columns have two types: `fields` and `tags`.  In general, you query for a `field`, and you can optionally filter by a `tag` (and/or a timestamp). A single record in a measurement is called a `Point`.

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

Here are some example queries that demonstrate usage of the retention policies, measurements, fields, and tags described above.

### InfluxDB Query Examples

{: .note-cream }
By default, all data is stored into the Influx database in UTC time. This means that to get accurate results from your CLI queries, you'll need to specify the timezone with the `TZ()` function.  See the [official list of timezones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List) and find the `TZ database name` from the list that corresponds to your timezone.

1. Get the maximum amperage from CT1 over the last 3 days.

    ```
select max(current) from raw_cts where ct = '1' and time >= now() - 3d TZ('America/Los_Angeles');
    ```

    <details markdown="block">
    <summary>Sample Output (click to expand):</summary>    
    {: .text-delta}
```    
name: raw_cts
time                     max
----                     ---
2023-02-20T04:30:04.107Z 28.84763731367289
```
    > The unit for `max` in this query is amperes (A).
    </details>

{:style="counter-reset:step-counter 1"}
2. Get the total energy produced from all [`production`](./configuration#type) CTs from February 20, 2023.

    ```
select sum(energy) from rp_5min.solar_energy_5m where time >= '2022-02-20 00:00:00' and time <= '2022-02-20 23:59:00' GROUP BY TIME(1d) TZ('America/Los_Angeles')
    ```

    <details markdown="block">
    <summary>Sample Output (click to expand):</summary>    
    {: .text-delta}
```
name: solar_energy_5m
time                      sum
----                      ---
2023-02-20T00:00:00-08:00 49.751555818786514
```

    > The unit for `sum` in this query is kilowatt-hours (kWh).
    </details>


{:style="counter-reset:step-counter 2"}
3. Get the total energy imported for the month of January 2023.

    ```
select sum(energy) from rp_5min.net_energy_5m where energy > 0 and time >= '2023-01-01 00:00:00' and time < '2023-02-01 00:00:00' TZ('America/Los_Angeles')
    ```

    <details markdown="block">
    <summary>Sample Output (click to expand):</summary>    
    {: .text-delta}
```
name: net_energy_5m
time                      sum
----                      ---
2023-01-01T00:00:00-08:00 650.1330642174386
```

    > The unit for `sum` in this query is kilowatt-hours (kWh).
    </details>


{:style="counter-reset:step-counter 3"}
4. Get the average daily home power draw for the last 7 days.

    ```
select mean(power) from rp_5min.home_load_5m where time >= now() - 7d GROUP BY time(1d) TZ('America/Los_Angeles')
    ```

    <details markdown="block">
    <summary>Sample Output (click to expand):</summary>    
    {: .text-delta}
```
name: home_load_5m
time                      mean
----                      ----
2023-02-14T00:00:00-08:00 1362.6262039071523
2023-02-15T00:00:00-08:00 1378.8063124919058
2023-02-16T00:00:00-08:00 1500.676864039368
2023-02-17T00:00:00-08:00 1668.0716463994613
2023-02-18T00:00:00-08:00 1553.348705943601
2023-02-19T00:00:00-08:00 1344.7927897131085
2023-02-20T00:00:00-08:00 1417.371858485695
2023-02-21T00:00:00-08:00 1440.8402693540943
```

    > The unit for `mean` in this query is Watts (W).


    {: .note-cream }
    Since this sample query uses `now() - 7d` as the time filter, we know it will always fall within the 30 day window in which the high resolution data is stored. So, it would have been perfectly valid
    to query `from home_load` instead of `from rp_5min.home_load_5m`, but, it would have been significantly more computationally expensive, as the high resolution data in `home_load` has nearly **2 million** more data points than the `home_load_5m` measurement does over the same time interval!
    ```
    > select count(power) from home_load where time >= now() - 7d;
    name: home_load
    time                           count
    ----                           -----
    2023-02-15T02:53:39.664580542Z 1988332
    > select count(power) from rp_5min.home_load_5m where time >= now() - 7d;
    name: home_load_5m
    time                           count
    ----                           -----
    2023-02-15T02:53:50.707123813Z 2014
    ```

    </details>



{: .reference-cream }
[https://docs.influxdata.com/influxdb/v1.8/query_language/explore-data/](https://docs.influxdata.com/influxdb/v1.8/query_language/explore-data/)



## Backups
InfluxDB includes a built in command-line backup mechanism.  I have incorporated this functionality into a backup script included with this project, which automatically backs up your Influx data and power monitor configuration, and stores it on an external USB flash drive. See [Enabling Automatic Backups](configuration#enabling-automatic-backups) for more info.

For the native InfluxDB backup mechanism, see the official docs below:

{: .reference-cream }
[https://docs.influxdata.com/influxdb/v1.8/tools/influxd/backup/](https://docs.influxdata.com/influxdb/v1.8/tools/influxd/backup/)