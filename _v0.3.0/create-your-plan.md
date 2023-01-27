---
layout: default
title: Create Your Plan
---

## Create Your Plan


### Introduction
The power monitor supports six total current sensors, so you'll need to determine which six circuits you want to monitor.

For whole-home monitoring, you don't need to monitor every circuit. You can capture your entire home's usage just by measuring the main feed (or both main feeds if in North America). The "mains", as they're referred to, connect from the electrical meter to the main breaker in your panel.  I will assume that you are in North America with a 120V, 60Hz grid connection, delivered over two legs.  If you are outside North America and have a grid voltage of 230V at 50Hz, you will only have one main (unless you have three-phase service).

If you are more interested in specific usage for items like electric-vehicle chargers, air-conditions & heat pumps, etc, make sure you can identify the circuit breakers that power those specific circuits. 

Lastly, if you have a generator, or a grid-tied solar inverter, (or any other source of grid-tied production), make sure you have identified the breakers that connect to those systems.

### Planning
As mentioned above, whole-home monitoring requires only to measure the mains.  So, make a note the rating of the big main breaker that feeds the panel. The labels are often stamped directly into the toggle switch of the breaker, or on the circuit breaker body itself.

Next, make a note of the rating of any additional circuits you want to measure.  Also make note of the "width" of the breaker (is it 1-pole, or 2-pole?) You should have something like this:

* Mains: 200A (typically always 2-pole in North America)
* Solar Inverter: 80A (2-pole)
* AC Unit #1:     30A (2-pole)
* AC Unit #2:     30A (2-pole)
* Tesla Charger:  60A (2-pole)

With the two mains, and four additional circuits, this will fully populate the monitor's six inputs.

Next, your electrician will need to de-energize the panel and remove the panel cover to check the diameter of the mains.  Even with the main breaker turned off, the mains are still live, so the electrician will still need to excercise extreme caution in working around the mains.  The diameter of the mains is important to check so you know what size sensor to purchase.

---

The final part of the plan is the location to install the power monitor.  The sensor wires are only 2 meters long, but they can be extended by attaching the leads to a shielded cat5e cable.  The Power Monitor needs two outlets - one to power the Raspberry Pi, and one to measure the grid voltage via the 9V AC step-down transformer.  I highly recommend mounting a 200mm H x 155mm L x 80mm D ABS plastic junction box near the panel and an existing AC outlet to house the power monitor and cabling.  The enclosure should not be installed in direct sunlight to prevent overheating, so indoors is ideal.

### Summary

Now that you have your plan, you're ready to [purchase the hardware](./acquire-the-hardware).

If this page did not answer your questions for planning, please see [the FAQ](/FAQ).