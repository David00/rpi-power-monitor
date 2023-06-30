---
title: Software Installation
parent: General
grand_parent: Documentation
nav_order: 3
layout: default
---


# Software Installation
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>

## Prebuilt OS Image
The recommended way to setup and use this project is with the provided prebuilt [Raspberry Pi OS Image](https://github.com/David00/rpi-power-monitor/releases). 

<p class='text-center' id='os-download-btn'>
<button type='button' name='button' class='btn' style='background-color:#457B9D;'>
    <a class='h2' style='color:#F1FAEE;' href="https://github.com/David00/rpi-power-monitor/releases/download/{{site.latest-os-image}}/Raspberry-Pi-OS-Lite_rpi_power_monitor-{{site.latest-os-image}}+release.zip">Download {{ site.latest-os-image }} from GitHub</a>
</button>
</p>

The provided Pi OS image is simply the stock Raspberry Pi OS Lite image with all the dependencies pre-installed, and it is suitable for offline installations. Simply download the file and use Raspberry Pi Imager to write the image to your microSD card.

{: .note-aqua }
If you don't want to use the prebuilt image, see [Manual Installation]({{site.baseurl}}/docs/{{site.latest-version}}/manual-installation).

## Pre-configure Wi-Fi 

You can configure your Wi-Fi network before booting your Raspberry Pi, so that it will connect to your network automatically on first boot. After you have flashed the custom image to your microSD card, reconnect the card to your computer, and open up the file named `rpi_power_monitor-wpa-supplicant.txt` inside the `boot` folder.

If you have a standard WPA2 protected wireless network, find the section beginning with `WPA/WPA2 secured` and uncomment all of the lines. Then, add your network name (SSID) and password (psk), leaving the quotation marks.

<details open markdown="block">
<summary>Example</summary>
```
# WPA/WPA2 secured
network={
  ssid="My WiFi Name"
  psk="topsecretpassword"
}
```
</details>

Next, scroll down to set the country code.  A few examples are there - just make sure only one is uncommented, and leave the rest commented out.

Save and close the file.  The microSD card is now ready to be used in your Raspberry Pi.


{: .note-aqua }
The custom image is command-line only (no desktop). You should be familiar with using SSH and basic command line instructions.


## First Boot

If you followed the pre-configure wifi section above, your Pi should connect to your wireless network automatically when it starts up. You'll probably need to take a look at your router's client table to find the Pi's IP address, or use a scanning tool like Fing, Angry IP Scanner, or Nmap. If you can't find your Pi's IP address, or don't know how to use SSH, connect a keyboard and monitor to the Pi.  ([Here's the official Raspberry Pi documentation for connecting with SSH](https://www.raspberrypi.com/documentation/computers/remote-access.html))

{: .note-aqua }
The SSH credentials for the custom OS image have been left as default (username: **pi** password: **raspberry**). 


To continue the setup, see the Configuration page for the specific release that you are using. The latest release is {{ site.latest-version }} and its configuration page is here:

## [ Go to {{ site.latest-version }} Configuration]( {{site.baseurl}}/docs/{{ site.latest-version }}/configuration ){: .btn .btn-blue }