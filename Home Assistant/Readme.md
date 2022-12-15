## Home Assistant Integration

The best and most reliable way to do this is to first have your Home Assistant server using storage that isnt a micro SD card (common for basic HA set-ups using a Raspberry Pi). The issue with SD cards is they burn out quickly when they are constantly being written to. My setup, for example, is a Raspberry Pi 4b 8gb in an Argon One M.2 case with a 240gb m.2 Sata Drive. Really, any USB drive will do (hard disk or SSD). You'll need to set your RPi to boot from USB. I wont get into how to set that up. There is plenty of documentation on how to do this. This also isnt the only way, but again, I wont get into it. IF you have your HA set up a different way, you're already way smarter than I am and already know how to setup things up with your rig.

The other option is to continue to use the RPi Power Monitor as your influxdb "server" but again, keep in mind you're on borrowed time with your SD card. Make sure you have a high quality name brand SD card rated at A1 or higher. If you plan to use your RPi Power Monitor as the InfluxDB server, scroll down to the "Setting Up Sensors" section.

---

## Using You Home Assistant Server

1.) You'll need to first install the InfluxDB Add-On. The installation of this add-on is pretty straightforward and not different in comparison to installing any other add-on.

    A.) Search for the “InfluxDB” add-on in the add-on store and install it.
    B.) Start the “InfluxDB” add-on.
    C.) Make sure "Start on Boot" and "Show in Side Bar" are turned on
    D.) Check the logs of the “InfluxDB” to see if everything went well.
    E.) Click the “OPEN WEB UI” button!
  
2.) Next you need to set up a database.

    A.) Click the Crown Icon (InfluxDB Admin)
    B.) Within the Database tab, click "Create Database"
    C.) Name the new database power_meter
    D.) Click the green check mark
    
3.) Now you need to set up a user

    A.) Click the Users tab within the InfluxDB Admin menu (tab below Database)
    B.) create username and password. DO NOT USE SPECIAL CHARACTERS.
    C.) click the green check mark
    D.) click the -- under permissions and set to all
    E.) click apply
    
4.) Tell your RPi Power Monitor what InFluxDB server to use

    A.) SSH into your RPi Power Monitor
    B.) run the command  nano ~/rpi_power_monitor/rpi_power_monitor/config.py
    C.) scroll to the # InfluxDB Settings
    D.) change the host from 'localhost' to what ever your local IP address is for you HA server. Example '192.168.1.20'
    E.) change the username to what ever you created in step 3-B. Example 'homeassistant'
    F.) change the password to what ever you created in step 3-B. Example 'password'
    G.) exit and save the file
    H.) Update the rpi_power_monitor module with the changes you just applied:
    
        cd ~/rpi_power_monitor
        pip install .
 
            
5.) Lets now verify you have data flowing into the HA InfluxDB

    A.) On your HA home page, open up the InfluxDB GUI.
    B.) Click the line graph icon (explore)
    C.) Click Add a Query
    D.) under DB.RetentionPolicy, you should see the list autopopulate. Click power_monitor.autogen
    E.) under "Measurements & Tags" you should see home_load, net, raw_cts, solar, voltages. net and raw_cts will have sub options.
    F.) each one should have at least on option under "Fields" depending on the measurement chosen.
    G.) make sure each field for each measurement is populating data
    
---
    
## Setting Up Sensors

This part will require you to make changes to your configuration.yaml file within Home Assistant. Make sure to create a full back-up just incase you make an uh-oh and cant figure out what you did. Better to be safe than sorry! The easiest way to make these changes is to have the File Editor Add-On, and to have it set to show up in the side bar.

1.) Open your configuration.yaml file

2.) add the following lines, making sure to input your influxdb servers local ip address in the "host:" line. Depending on what option you chose, this will be your HA sever IP or RPi Power monitor IP address.

```
influxdb:
  host: 
  username: !secret influxdb_user
  password: !secret influxdb_pass
  exclude:
    entity_globs: "*"
    
homeassistant:
  packages: !include_dir_named packages
  customize:
    sensor.home_power_useage:
      device_class: energy
      unit_of_measurement: kWh
```

3.) click the red disk icon (save)

4.) in the same folder as your configuration.yaml file ( config/ ) you'll want to create a folder called packages if you dont have one already

5.) open the packages folder, and create a file called RPiEnergyMonitor.yaml

6.) copy the contents from the file of the same name in this repository into this file, again making sure to put your HA server or RPi Power Monitor local ip address in the "host:" line, depnding on what you chose to use for your InfluxDB "server".

7.) within this file, you can customize the "name:" field to what ever you want to for each sensor. Example: House Main 1, Dryer, Furnace. You can also change the update frequency here as well in the "where:" field. Default is 1m.

8.) once you are done, click the red disk icon (save)

9.) head back to your config/ folder. Depending on what version of HA you are running, you should have a secrets.yaml file. If not, create it. Once in that file, add the following lines. This is where you will enter the username and password for your influxDB server. Depending on the option you chose, itll be the ones you created for your HA infludxDB server, or the default username and password used in the config.py file on the RPi Power Monitor.

```
influxdb_user:
influxdb_pass:
```

10.) click the red disk icon (save)

11.) lastly, we want to go to the "Developer Tools" menu. It defaults to the YAML tab. From there you'll want to click the "Check Configuration" and make sure there are no errors. If after the check, you get "Configuration will not prevent Home Assistant from starting!" you will then click "Restart". Once HA has restarted, your sensors will start to populate!

---

### Energy Dashboard Integration

If you now want to be able to track your sensors in the Energy Dashboard under "Monitor Individual Decives", AND most importantly, have your whole home use be tracked in the Energy Usage grid, we will now have to do a few more things.

1.) First, you'll go to "Settings", then "Devices and Services". The default tab that opens is integrations. Click "Helpers".

2.) click "Createt Helper" down in the lower right corner.

3.) select "Integration - Riemann sum integral sensor". From here, the name and sensor will depend on which one you choose. I'll write the steps assuming you used the fault names. If you changes the names, use the names you changed the default ones to.

4.) Name will be CT-1 Total. For Sensor, you will scroll until you find the one named ct-1 power. Integration method will be "Trapezoidal rule". Precision will be 2. Metric prefix will be k (kilo). Time unit will be h (hours).

5.) repeat steps 2-4 for each CT (total of 6).

6.) give time for the new sensors created by this helper to populate statistics before adding them to the Energy Dashboard. They update every minute (unless you changed the update time when during the " Setting up Sensors" steps).

7.) Now, we want to go to Settings, then Dashboards.  From there we will select Energy.

8.) Within the Electric Gird card, you'll select "Add Consumption". From the drop down, you should find sensor.home_power_usage. From there, if you know your price per kWh, you can select "Use a Static Price" and input it there. Slick Save. You will NOT see your grid consumption show up right away. It typically takes about 2 hours for this data to populate into that graph.

9.) Lastly, go to the Individual devices card and select Add device. You'll look for the new "helper sensors" you created in steps 1-4. The helper screen will show the names of the sensors they created. You MUST select those sensors (and should be the only ones for those CTs that show). AGAIN, it takes up two 2 hours or more for those to start populating data in the Individual devices grid, depending on how much power is being used.

10.) Enjoy your beautiful Energy Data in Home Assistant!

