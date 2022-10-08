# Power Monitor HAT (for Raspberry Pi)

This project is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time, including accurate consumption, generation, and net-production. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

This project is derived from and inspired by the resources located at https://learn.openenergymonitor.org. 

---

## Where can I get it?

I am offering DIY kits, factory-assembled PCBs, and a variety of current transformers to use with this project.

Please see https://power-monitor.dalbrecht.tech/ for more information.

---

## How do I install?

There are two ways to install.

### Clone the repository

```bash
git clone https://github.com/David00/rpi-power-monitor
```

Then, to run, for example:

```bash
cd rpi-power-monitor
python -m virtualenv ./venv
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python ./rpi_power_monitor/power_monitor.py terminal
```

### Install python package

```bash
python -m virtualenv ./venv
./venv/bin/python -m pip install git+https://github.com/David00/rpi-power-monitor.git
```

Then, to run, for example:

```python
from rpi_power_monitor import power_monitor

rpm = power_monitor.RPiPowerMonitor()
rpm.run_main()
```

Additionally, you can run, for example:

```python
from rpi_power_monitor import power_monitor

grid_voltage = 124.2
transformer_voltage = 10.2

ct1_phase_correction = 1.0
ct2_phase_correction = 1.0
ct3_phase_correction = 1.0
ct4_phase_correction = 1.0
ct5_phase_correction = 1.0
ct6_phase_correction = 1.0

ct1_accuracy_calibration = 1.0
ct2_accuracy_calibration = 1.0
ct3_accuracy_calibration = 1.0
ct4_accuracy_calibration = 1.0
ct5_accuracy_calibration = 1.0
ct6_accuracy_calibration = 1.0
ac_accuracy_calibration = 1.0

phase_correction = {
    'ct1': ct1_phase_correction,
    'ct2': ct2_phase_correction,
    'ct3': ct3_phase_correction,
    'ct4': ct4_phase_correction,
    'ct5': ct5_phase_correction,
    'ct6': ct6_phase_correction,
}

accuracy_calibration = {
    'ct1': ct1_accuracy_calibration,
    'ct2': ct2_accuracy_calibration,
    'ct3': ct3_accuracy_calibration,
    'ct4': ct4_accuracy_calibration,
    'ct5': ct5_accuracy_calibration,
    'ct6': ct6_accuracy_calibration,
    'AC': ac_accuracy_calibration,
}

sensor = power_monitor.RPiPowerMonitor(
    grid_voltage=grid_voltage,
    ac_transformer_output_voltage=transformer_voltage,
    ct_phase_correction=phase_correction,
    accuracy_calibration=accuracy_calibration)

board_voltage = sensor.get_board_voltage()

samples = sensor.collect_data(2000)

rebuilt_waves = sensor.rebuild_waves(
    samples,
    sensor.ct_phase_correction['ct1'],
    sensor.ct_phase_correction['ct2'],
    sensor.ct_phase_correction['ct3'],
    sensor.ct_phase_correction['ct4'],
    sensor.ct_phase_correction['ct5'],
    sensor.ct_phase_correction['ct6'])

results = sensor.calculate_power(rebuilt_waves, board_voltage)

print(f"Voltage: {board_voltage}")

chan = 1
for ct in range(1, 7):
    print(f"Power {chan}: {results[f'ct{ct}']['power']} W")
    print(f"Current {chan}: {results[f'ct{ct}']['current']} A")
    print(f"Power Factor {chan}: {results[f'ct{ct}']['pf']}")
    chan += 3
```

---

## What does it do?

This code accompanies DIY circuitry that supports monitoring of up to 6 current transformers and one AC voltage reading. The individual readings are then used in calculations to provide real data on consumption and generation, including the following key metrics:

* Total home consumption
* Total solar PV generation
* Net home consumption
* Net home generation
* Total current, voltage, power, and power factor values
* Individual current transformer readings
* Harmonics inspection through a built in snapshot/plotting mechanism.

The code takes tens of thousands of samples per second, corrects for phase errors in the measurements, calculates the instantaneous power for the tens of thousands of sampled points, and uses the instantaneous power calculations to determine real power, apparent power, and power factor. This means the project is able to monitor any type of load, including reactive, capacitive, and resisitve loads.

---

## Where can I get it?

I am offering DIY kits, presoldered PCBs, and a variety of current transformers to use with my project.

Please see https://power-monitor.dalbrecht.tech/ for more information.

---

## Installation & Documentation

### Please see the [project Wiki](https://github.com/David00/rpi-power-monitor/wiki#quick-start--table-of-contents) for detailed setup instructions.

---

## Contributing

Would you like to help out? Shoot me an email at github@dalbrecht.tech to see what items I currently have pending.

---

### Credits

* [OpenEnergyMonitor](https://openenergymonitor.org) and forum member Robert.Wall for guidance and support

* The `spidev` project on PyPi for providing the interface to read an analog to digital converter

---

### Like my project? Donations are welcome!

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=L6LNLM92MTUY2&currency_code=USD&source=url)

BTC:  1Go1YKgdxAYUjwGM1u3JRXzdyRM938RQ95

###### Last Updated:  October 2022
