---
title: 3 Phase Variant Setup
layout: default
nav_exclude: true
search_exclude: true
---

# 3-Phase Setup Guide
{: .no_toc }

#### March 2023 | v0.3.0
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>

---

## Overview

The setup of this software follows the same general process used in the published single-phase version, which is:

1. Set the grid voltage and AC transformer output voltage in `config.toml`
2. Set each input channel up in `config.toml` to reflect the rating for the sensor you're using.
3. Conduct the phase calibration process using a resistive load, which performs some measurements and calculations, and provides you with a value to apply to `config.toml`.
4. Final calibration and operation

---

## Limitations

To fully monitor a three phase system, it would require three voltage inputs - one from each of the phases. The power monitor PCB only has one voltage input, which means it can't collect the voltages from two out of the three phases. I have implemented a workaround to apply the voltage measurement to the other two phases, but this will create an inaccuracy in the power calculation on two of the three phases if the voltage levels are different on those two phases.

Suppose you have 3 phases (A, B, C), and 3 current sensors (ct1, ct2, ct3).  If your AC voltage transformer is plugged into phase B, it only has access to this phase's voltage level. Real three-phase monitoring would need a voltage measurement from each phase, but unfortunately we don't have that. So, we'll have to use phase B's voltage measurements and apply them to the power calculations for phase A and phase C.  The voltage is usually different between the three phases, so by applying phase B's voltage to phase A and phase C, we're introducing an error in the power calculation.  The magnitude of the error corresponds to the magnitude of the difference between the actual voltage of phase A and phase B (likewise, between phase C and phase B).  The amperage measured will still be correct since the sensors directly measure this - it's just the real power calculation that can vary.

Finally, the calibration process can be tricky because it requires access to each of the three phases in a single location (or extension cords that can connect to each of the three phases).

---

## Initial Setup Process

{: .note-cream }
If you have already used your Raspberry Pi with a previous version of this project, you might already have the `~/rpi_power_monitor` folder.  You can check it with the following command:

```
ls ~/rpi_power_monitor
```

* If you see `ls: cannot access '/home/pi/rpi_power_monitor': No such file or directory`, then you can proceed with step 1 below.  
* If you instead see files and folders, the easiest thing to do is just to rename the existing `rpi_power_monitor` folder before starting step 1.  You can rename the existing folder with: 

    ```
    mv ~/rpi_power_monitor ~/rpi_power_monitor_old
    ```

1. Create a new folder and clone the project to the new folder:   

    ```
    mkdir ~/rpi_power_monitor
    cd ~/rpi_power_monitor
    git clone https://github.com/David00/rpi-power-monitor.git .
    git checkout feature/v0.3.0-3phase-integration
    ```

1. Install the new release with Pip (note the period at the end!):

    ```
    pip3 install .
    ```

1. Download the new `config.toml` file from the new docs site:

    ```
    cd ~/rpi_power_monitor/rpi_power_monitor
    wget https://david00.github.io/rpi-power-monitor/docs/v0.3.0-beta/config.toml
    ```

1. Go through the section in the docs titled [Configuring your Power Monitor](configuration.html#configuring-your-power-monitor).


1. Make sure the power monitor is not running the background before continuing:

    ```
    sudo systemctl stop power-monitor.service
    ```

## 3-Phase Specific Setup

1. Connect your AC voltage transformer to the outlet where you intend to leave it permanently connected. If your voltage transformer can be plugged in the opposite way (like in North America and some European outlets), make a mental note about which way it's oriented.

2. Make the following changes to `config.toml`.  In the `[general]` section:

    - set `three_phase_mode = true`.



## Phase Calibration

This section covers the process for measuring the phase difference between your phases, and applying the measurement to the config file.  This is needed to implement the workaround that lets us use the voltage measurements from one phase for the other two phases.

This process requires a purely resistive load, which is usually something that produces a lot of heat.  High-power halogen work lamps (500W+) are ideal because their output is purely resistive and consistent, but electric kettles, irons, etc, can also be used.


#### Process Overview 

* Install the sensors on your mains in the electrical panel. 
* Connect your resistive load to an outlet that is connected to one of the three phases.
* Attempt to remove all other loads on that phase, either by disconnecting them from the outlet, or turning off the circuit breakers at the electrical panel.
* Run the software in phase calibration mode, and update the config file.
* Repeat for the other two phases.
* Compare the power monitor's measured amperage to the amperage shown by a hand-held AC current meter.


{: .note-aqua }
For the best results, you'll need to use a load whose current is at least 10% the rating of your sensor. Example: With a 20A sensor, you'll want at least a 2A load. For a 100A sensor, you'll want at least a 10A load.
<br>
Problems with this process are almost always due to not using a large enough load.

If you don't have a resistive load large enough to draw at least 10% the rating of your sensor, you'll need a larger load, or, you can use the [extension cord loop trick](https://github.com/David00/rpi-power-monitor/wiki/Phase-Correction-Procedure#current-multiplication-example).  Using the extension cord loop trick means that you can't calibrate the sensors directly in the electrical panel, which complicates the install, because the CT sensor that connects to the looped extension cord will still need to connect to the power monitor PCB.  The instructions below assume that your test load draws enough current and that you'll be proceeding with the in-panel installation and calibration.


<details open markdown="block">
<summary id="in-panel-calibration-steps" class='text-gamma'>In-Panel Calibration</summary>

1. Assuming you have three sensors, connect each one over one of the main phases in your electrical panel.  In `config.toml`, make sure that the type is set to `mains`.  If the sensor is not measuring your mains, it should be set to either `consumption` or `production` as outlined in the [configuration reference manual](configuration#type).

2. Identify which outlets are fed by which phase - you'll need access to an outlet on all three phases during this process.  Also, identify which sensors are monitoring which phase.

3. Connect your resistive load to an outlet on one of the phases, and turn it on.

4. Start the power monitor in phase calibration mode with the following commands:

    ```
    cd ~/rpi_power_monitor/rpi_power_monitor
    python3 power_monitor.py --three-phase-calibrate
    ```

5. The power monitor will display (in the terminal) the measured phase angle for each of the channels that are enabled in `config.toml`. So, you'll need to know which phase your load is connected to during this process.

    <details markdown="block">
    <summary>Sample Output (click to expand)</summary>
    ```
    ...many lines removed from above...
    ct1 : 4.69 ct2 : 105.50 ct3 : 126.73
    ct1 : 4.26 ct2 : 111.41 ct3 : 129.21


    Overall Averages:
    1 : 4.59 deg
    2 : 122.47 deg
    3 : 125.88 deg
    ```

    > In the example, my 500W halogen lamp was connected to the same phase as my voltage transformer, and CT 1 was measuring the current, hence the low phase angle. 
    </details>

    {: .note-aqua }
    If you see values that are close to 60, 180, or 300 during calibration, then the sensor reporting that value is clamped over the conductor backwards.  This will cause the power monitor to report negative readings. To fix it, you can set `reversed = true` in `config.toml`, or, you can unclip the sensor, and reverse the way it clamps over the conductor. You can also reverse the wire polarity on the power monitor board's terminal block.
        

6. Edit `config.toml` and set the `phase_angle` value for the CT measuring your load equal to the value displayed in `Overall Averages`. 

    <details markdown="block">
    <summary>Example (click to expand)</summary>
        
    ```
    Contents of config.toml: 

    [current_transformers.channel_1]
    name = 'Channel 1'
    rating = 30
    type = 'consumption'
    two_pole = false
    enabled = true
    calibration = 1.0
    watts_cutoff_threshold = 1
    reversed = true
    phase_angle = 4.59
    ```
    </details>

7. Move your resistive load to another outlet on a different phase, and repeat these steps.
</details>

## Final Accuracy Calibration

The last part of the calibration process involves making sure that the amperage reported by the CT sensors is accurate. You'll need a handheld AC clamp meter to do this part.

#### Process Overview 

* Turn on various devices that are fed by the panel. Devices that use current in a stable manner will help the power monitor results be less-sporadic, but in general, the more current you can consume for this part, the better.
* Compare the readings of the power monitor to the reading of your handheld AC clamp meter.
* Update config.py, restart the power monitor, and compare the readings.
* Repeat for each CT.


{: .note-aqua }
The requirement for only using the resistive load is gone for this step, however, you may still want to use it on each phase to increase the amount of current flowing on the phase that you're checking the accuracy of.


1. Start the power monitor in `terminal` mode:

    ```
    cd ~/rpi_power_monitor/rpi_power_monitor
    python3 power_monitor.py --mode terminal
    ```

2. Clamp your handheld current meter over the same conductor as one of your CTs.

3. Observe the current reading from the power monitor and compare it to the reading of your handheld clamp meter.

4. If the values are not close, determine the calibration value needed by dividing the handheld clamp meter's reading by the power monitor's reading.

    <details markdown="block">
    <summary>Example (click to expand)</summary>

    Power Monitor Output:
    ```
    +-------------+----------+--------+--------+-----+-----+-----+
    |             |   ct1    |  ct2   |  ct3   | ct4 | ct5 | ct6 |
    +-------------+----------+--------+--------+-----+-----+-----+
    |    Watts    | 1248.89  | 21.036 | 22.339 |  0  |  0  |  0  |
    |   Current   |  9.396   | 0.158  | 0.167  |  0  |  0  |  0  |
    |     P.F.    |  0.997   |  1.0   |  1.0   |  0  |  0  |  0  |
    |   Voltage   |  133.35  |        |        |     |     |     |
    | Sample Rate | 19502.54 |  SPS   |        |     |     |     |
    +-------------+----------+--------+--------+-----+-----+-----+
    ```

    CT1's current is 9.396, but my handheld clamp meter shows 10.51.  So:

    ```
    calibration = 10.51 / 9.396 = 1.118
    ```

    So, I will set the calibration value in `config.toml` for channel 1 to `1.118`:

    ```
    [current_transformers.channel_1]
    name = 'Channel 1'
    rating = 30
    type = 'consumption'
    two_pole = false
    enabled = true
    calibration = 1.118
    watts_cutoff_threshold = 1
    reversed = false
    phase_angle = 4.59
    ```
    </details>

5. Stop the power monitor with `Ctrl-c` and restart it in terminal mode like before to compare the readings again.

    <details markdown="block">
    <summary>Example (click to expand)</summary>

    Channel 1 now shows the correct current that is fairly close to what my handheld meter shows.
    ```
    +-------------+----------+--------+--------+-----+-----+-----+
    |             |   ct1    |  ct2   |  ct3   | ct4 | ct5 | ct6 |
    +-------------+----------+--------+--------+-----+-----+-----+
    |    Watts    | 1397.363 | 22.817 | 22.801 |  0  |  0  |  0  |
    |   Current   |  10.52   | 0.171  | 0.171  |  0  |  0  |  0  |
    |     P.F.    |  0.997   |  1.0   |  1.0   |  0  |  0  |  0  |
    |   Voltage   |  133.25  |        |        |     |     |     |
    | Sample Rate | 19670.41 |  SPS   |        |     |     |     |
    +-------------+----------+--------+--------+-----+-----+-----+
    ```
    </details>

6. When you're all finished, stop the terminal mode output with `Ctrl-c`. Then, you can start the power monitor in the background with:

    ```
    sudo systemctl start power-monitor.service
    ```

    If you get an error when starting the power monitor in the background, see the instructions here to create the service file:

    <h2><a href="advanced-usage#creating-the-service-file">Running as a Service</a></h2>