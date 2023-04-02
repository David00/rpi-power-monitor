---

title: FAQ
nav_order: 10

---

# FAQ
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>

## General


## Hardware

<details markdown="block">
<summary id="can-i-use-to-monitor-X" class="fs-5">Can I use this to monitor _____?</summary>
{: .text-delta }
This project is only capable of monitoring AC power systems, including North American 120V 60Hz grids, and Eurasian 230V 50 Hz grids.

Adaptations to monitor other systems like DC power, gas, and water, are not supported.

</details>


## Software

<details markdown="block">
<summary id="how-do-i-determine-which-software-version-i-have" class="fs-5">How do I determine which software version I have?</summary>
{: .text-delta }

The most recent versions (v0.2.0 and above), you can run the following command in your terminal:

`pip list --format=freeze | grep "rpi-power-monitor"`

If this doesn't show anything, then you are likely on an old pre-v0.2.0 version.

If you installed the custom OS, the OS build version can be determined by running the following command:

`cat /root/rpi_power_monitor_os-version.txt`

If you see `No such file or directory`, then you are likely on the original v0.1.0 version that did not have this file.

Unless you have updated your power monitor software, the OS build version should match the power monitor code version.

</details>


<details markdown="block">
<summary id="how-do-i-determine-which-software-version-i-have" class="fs-5">How do start the power monitor automatically on boot?</summary>
{: .text-delta }
You need to create and/or enable the `power-monitor.service` file. See [Running As a Service]({{site.url}}/docs/v0.3.0/advanced-usage.html#running-as-a-service) for specific instructions.
</details>


## Troubleshooting

<details markdown="block">
<summary id="how-do-i-determine-which-software-version-i-have" class="fs-5">I can't access Grafana</summary>
{: .text-delta }
First, make sure Grafana is running with the command:

```
sudo systemctl status grafana-server
```

You should see `Active: active (running)` near the top of the output, like this:

<details open markdown="block">
<summary>Click to expand</summary>
```
$ sudo systemctl status grafana-server
● grafana-server.service - Grafana instance
    Loaded: loaded (/lib/systemd/system/grafana-server.service; enabled; vendor preset: enabled)
    Active: active (running) since Tue 2023-02-21 01:23:44 GMT; 1 months 9 days ago
```
</details>

If you don't see `active (running)`, then you can try to restart the service with the following command:

```
sudo systemctl restart grafana-server
```

If Grafana refuses to start, you can check the logs for an indication with the following command:

```
sudo journalctl -u grafana-service -n 25
```

This should give some indication of the problem which you can use to research online.

</details>