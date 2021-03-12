# Raspberry Pi Power Monitor

The Raspberry Pi Power Monitor is a combination of custom hardware and software that will allow you to monitor your unique power situation in real time (<0.5 second intervals), including accurate consumption, generation, and net-production. The data are stored to a database and displayed in a Grafana dashboard for monitoring and reporting purposes.

This project is derived from and inspired by the resources located at https://learn.openenergymonitor.org and a fork from David's one: https://github.com/David00/rpi-power-monitor

---

## My modifications (See Hardware wiki page)
The software has not been really modified. I just made my own board to implement 6 current transformers (used 15A one) without the RJ45 as all cables are very close to the PI. 

I have also added a French's teleinfo interface for some integration later, following this tutorial : http://hallard.me/pitinfov12/. 

And a simple push button to be added on the GPIO3 (SCL) to turn off the raspberry, following this tutorial : https://howchoo.com/g/mwnlytk3zmm/how-to-add-a-power-button-to-your-raspberry-pi.

It would be also possibel to move the LED to TX pin, to get some RPI monitoring throught UART activity. You can read this thread and see if it can be interesting : https://howchoo.com/g/ytzjyzy4m2e/build-a-simple-raspberry-pi-led-power-status-indicator

> comment : this layout is made through EASYEDA to be able to purchase on JLCPCB. in realuty, the 6 jack connectors are really just spread, I have no margin as all male jack are really touching each others. I would recommend then to put 5 jack in a row and the 6th on the side. Also the teleinfo and voltage connectors are not on the right side as they touch the Ethernet connector. They shoudld be on the other side. 

> last point I would like to find a very small voltage transfo to implement/solder it on the breadboard. But I did not find the correct one. If anybody has a proposal...

> Maybe the voltage reference should be changed for a fixed voltage or a part that has already the integrated divider. Or some LDO to be fixed at 1.75V (not a common voltage) ? At the end, depending on your analog signal, a VREF at 1.5V would also work.

### Please see the [project Wiki] for my board example + layout. I also added there some usefull command under putty to get access to Influg without using Grafana and try there some queries. You will also find usefull comment for a Cost of Use dashboard under Grafana. 

### Keep an eye on David's wiki (https://github.com/David00/rpi-power-monitor/wiki#quick-start--table-of-contents) for detailed setup instructions and update. 

### If you are interested in the cost of use dashboard, see below the result. The dashboards (JSON format) are available in the DOC folder. See also the wiki to tweak them.
![](https://github.com/DuduNord/rpi-power-monitor/blob/master/docs/Grafana%20global.png)
