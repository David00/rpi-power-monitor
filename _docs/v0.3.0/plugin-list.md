---
title: Plugin List
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 10
---


# Supported Plugin List
{: .no_toc }

This page provdes an overview of various plugins for the Power Monitor for Raspberry Pi project.  Plugins on this page have been examined and approved by the project maintainer in coordination with the plugin author.  

{: .note-cream } 
Do you have an idea for a plugin that you'd like to see on this page? See [writing a plugin](plugins#writing-a-plugin)

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>


## 1. GPIO Controller (Example Plugin)

Author: David00
{: .no_toc }
{: .text-delta }

This plugin is a small, but functional, example of a working plugin.  It is intended to be used as a reference for others developing their own plugins.  However, as written, it will change the state of a single GPIO pin according to the current net power.

Documentation: [link](https://github.com/David00/rpi-power-monitor/tree/develop/v0.3.0-plugins/rpi_power_monitor/plugins/gpio_controller_example_plugin)
{: .no_toc }
{: .text-delta }