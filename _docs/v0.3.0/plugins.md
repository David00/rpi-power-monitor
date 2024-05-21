---
title: Plugins
parent: v0.3.0
grand_parent: Documentation
layout: default
nav_order: 9
---

# Plugins
{: .no_toc }

<details open markdown="block">
<summary>Table of Contents</summary>
{: .text-delta }
- TOC
{:toc}
</details>


## Overview

The plugin system provides users and developers with a standard interface for expanding upon the power monitor's functionality.

{: .note-cream }
This page is intended for those who want to build their own plugins.  For using a specific plugin, please refer to that plugin's specific README.md on the [Plugin List](plugin-list) page.

There are countless possibilities for plugin functionality. Here are some examples (not yet written) that the plugin system can be used to accomplish:

* Send the power monitor data to a different system
* Perform actions based on the data, like controlling a relay, or hooking into your own application
* Generate and send usage reports
* Send customized alerts

<small>Note that these are just examples of plugins you can build - these functionalities do not currently exist.</small>


## Writing a Plugin

{: .note-cream }
See the <a href="https://github.com/David00/rpi-power-monitor/blob/develop/v0.3.0-plugins/rpi_power_monitor/plugins/gpio_controller_example_plugin/gpio_controller_example_plugin.py">GPIO Controller plugin</a> for a real example of all of the concepts and guidelines in this section.

### Git checkout the `master` branch

{: .note-cream }
If you are developing directly on a Pi running the Custom OS Image, you'll have to update your git config file to allow it to fetch other branches with the following commands: 
<details markdown="block">
<summary>Click to expand instructions to update your git config</summary>
```
cd ~/rpi_power_monitor
sed -E s'|\+refs.+|+refs/heads/*:refs/remotes/origin/*|'g  ~/rpi_power_monitor/.git/config
git fetch
```
</details>

Checkout the `master` branch:
```
git checkout master
```

### Create your plugin files and folder

A convenience script has been created to initialize your plugin folder and files from the existing template.  To use the convenience script, locate it in the `rpi_power_monitor/plugins/` folder and run it with:

```bash
bash create_plugin.sh
```

Type in your plugin name - acceptable characters are `a-z|A-Z|0-9`.  The script will validate your plugin name and provide the name of the created folder.

<details markdown="block">
<summary>Example (click to expand)</summary>

```bash
pi@raspberrypi:~/rpi_power_monitor/rpi_power_monitor/plugins $ bash create_plugin.sh
Enter the name of your plugin:
sample plugin 2
Setting up plugin "sample_plugin_2" in /home/pi/rpi-power-monitor/rpi_power_monitor/plugins
Done! Created sample_plugin_2.py and README.md inside plugins/sample_plugin_2/
```
</details>

### Plugin Structure

All plugins must adhere to the following structure and naming conventions:

* The plugin must reside in a folder inside of `rpi_power_monitor/plugins`, and the folder name must match the name of the file containing the code for your plugin.
* The plugin must include the <a href="#required-functions">required functions</a>
* The plugin folder must contain A README.md (see <a href="#readme">README</a>) that follows the laid out structure.

The [convenience script](#create-your-plugin-files-and-folder) mentioned above will initialize a new plugin that follows the guidelines above.

{: .note-cream }
The name of your plugin folder and python file must be the same.  If you change one, make sure to change the other!


#### Required Functions
{: .fs-5 }

The following functions must be present in your plugin's main file (`plugin_name.py`).

#### `start_plugin(data, stop_flag, config, logger, *args, **kwargs)`
{: .fs-5 }
{: .no_toc }

##### Arguments
{: .no_toc }

* `data`: A dictionary that contains the latest power monitor data. The dictionary is shared among all plugins; therefore, please treat the dictionary as read-only (do not pop, insert, or update values within the dictionary).
* `stop_flag` : A Python `multiprocessing.Event` object that is used to signal the shutdown of the power monitor to all running plugins.
* `config` : A dictionary containing the parsed and converted TOML from your plugin's configuration, taken directly from `config.toml`.
* `logger` : A Python logging object that you can use to log messages to stdout.

This function must be included in your plugin file, and the function definition must be kept as-is.  You can think of the `start_plugin()` function as your plugin's main body.  The power monitor will call `start_plugin()` if the plugin is enabled in the `config.toml`.

If your plugin needs to run indefinitely while the power monitor is running, please use the existing `while not stop_flag.is_set()` block.  This is effectively a `while True` loop and will run as long as the power monitor is running, assuming your plugin doesn't encounter an unhandled exception. Code outside a `while not stop_flag.is_set()` block will only run when the plugin starts up. You can use your own `while not stop_flag.is_set()` elsewhere in your plugin if needed.

{: .pro-aqua }
The power monitor will **not** attempt to restart your plugin if it crashes.  Effective usage of `try`, `except`, and `finally` to handle raised exceptions will ensure your plugin continues running.

{: .danger }
Do not use Python's built-in `time.sleep(seconds)` function to put your plugin to sleep. This will cause the power monitor application to hang and appear unresponsive if it is shutdown while your plugin is sleeping. Instead, use the provided `sleep_for(seconds, stop_flag)` function, which will handle checking if the power monitor application is trying to be stopped or not.


Feel free to define other functions, create additional files in your plugin directory, and import them as necessary.

#### `stop_plugin()`
{: .fs-5 }
{: .no_toc }

This function must be included in your plugin file, and the function definition must be kept as-is.  This function is intended for running any cleanup procedures that your plugin might need before it stops running.  This function is called when the power monitor process is stopped. You can leave this function definition empty if your plugin does not need any cleanup procedures.

---

### Accessing the Power Monitor Data

Each time the power monitor measures a new batch of data, the `data` variable of the `start_plugin` function is updated. This typically happens up to three times per second. The `data` variable is a dictionary with the following structure. The values below are real values so that you can see the types for each:


```json
{
    "cts":{
        "1":{
            "power":-0.15614170241133654,
            "pf":-0.008707578629557584,
            "current":-0.01341197029282334,
            "voltage":133.23533164737233
        },
        "2":{
            "power":-0.018413940715636623,
            "pf":-0.0008359884096381318,
            "current":-0.1405852064282471,
            "voltage":133.2450403146403
        },
        "3":{
            "power":-0.3871674075367957,
            "pf":-0.020716933660741007,
            "current":0.1413622934508677,
            "voltage":133.2428933653774
        },
        "4":{
            "power":-0.18666605908420159,
            "pf":-0.009948353174774924,
            "current":0.14011308998509991,
            "voltage":133.24793799600786
        },
        "5":{
            "power":-0.20825052262125632,
            "pf":-0.01114300361840111,
            "current":0.14088852673526656,
            "voltage":133.2452814824922
        },
        "6":{
            "power":0.05813865566604561,
            "pf":0.0030650506064272562,
            "current":0.14096820400791774,
            "voltage":133.24494676750146
        }
    },
    "production":{
        "power":0.0,
        "pf":0.0,
        "current":0.0
    },
    "home-consumption":{
        "power":-0.1745556431269732,
        "current":0.15399717672107044
    },
    "net":{
        "power":-0.1745556431269732,
        "current":0.15399717672107044
    },
    "voltage":133.23533164737233
}
```

Remember, the data dictionary is updated by the power monitor process and is shared to all running plugins.  Your plugin should **not** make changes to this dictionary to avoid interfering with other plugins that want to use the data.


### Configuration File
Your plugin's config should go into the power monitor's `config.toml` file.  The power monitor will provide your plugin's config to the [`start_plugin`](#start_plugindata-stop_flag-config-logger-args-kwargs) function.  In `config.toml`, your plugin's config should look like the following, and it must have the `enabled =` setting, with a value of either `true` or `false`.

```toml
[plugins.YOUR_PLUGIN_NAME]
enabled = true
```

That's wraps up the requirements for the plugin configuration. You can add any values to your plugin config block and they will be accessible in the [`start_plugin`](#start_plugindata-stop_flag-config-logger-args-kwargs) function.

{: .note-cream }
For a sample plugin configuration, refer to the GPIO Controller example plugin's README <a href="https://github.com/David00/rpi-power-monitor/tree/develop/v0.3.0-plugins/rpi_power_monitor/plugins/gpio_controller_example_plugin#setup--usage">here</a>.


### Logging

`logger` is provided to `start_plugin`, and it is a standard [`logging.Logger`](https://docs.python.org/3/library/logging.html#logging.Logger) instance.  The power monitor will configure the logging level of your plugin to match the logging level of the main power monitor process, but you can override it in your plugin's configuration block in `config.toml`. Example:

```toml
[plugins.YOUR_PLUGIN_NAME]
enabled = true
log_level = 'DEBUG'     # See https://docs.python.org/3/library/logging.html#levels for a list of logging levels.
```

You can make logging calls at a specific level with:

```python
logger.info("This is an info message, which will only be shown if your plugin's logging level is set to INFO or below.")
logger.critical("This is a critical message.")
```

### README

If you intend to share your plugin, it must include a README.  This provides the user with a high level overview, setup instructions, and anything else you deem necessary about using your plugin. (Even if you don't intend to share your plugin, creating a README for yourself is a good practice and can help you later on!).

If you used the [plugin init script](#create-your-plugin-files-and-folder), a README.md template was created inside your plugin folder. Inside the README file, you'll find a basic layout and structure. In an effort to keep a standard feel for the plugin ecosystem, please keep the existing section titles and order as-is. Feel free to add sub-sections as needed, though!


## Sharing your Plugin

If you'd like to share your work and make your plugin available for other users, you can submit a pull request (PR) to have your plugin integrated into the Power Monitor for Raspberry Pi project.  Plugins whose PRs are approved will be added to the [Supported Plugin List](plugin-list).  You are also welcome to host your plugin in your own repo if you don't want to submit a PR; however, your plugin will not be added to the Supported Plugin List.

Before submitting a PR, please read and understand the following:

* You, as the plugin author, should be available to provide support for users that have questions/problems with using your plugin.
* I, as the project author, may not have access to or familiarity with specific integrations that your plugin provides, and cannot provide support for highly specific questions or issues.
* Please review and respect the licenses associated with any third-party packages your plugin uses. *Plugins that rely on third-party packages, whose licenses are incompatible with the licensing of this project, will not be added to the repository.*
* I reserve the right to remove plugins from the project at any time.

Please follow [Python best practices](https://peps.python.org/pep-0020/#the-zen-of-python) and use [proper formatting](https://peps.python.org/pep-0008/#code-lay-out), [docstrings](https://peps.python.org/pep-0257/), and [variable names](https://peps.python.org/pep-0008/#naming-conventions). 

### Creating a PR

1. [Create a fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo) of the project in your own Github repository
2. In your fork, build your plugin, README, and then validate that everything works.
3. [Create your PR](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork) from your fork.
4. We will review the PR and provide feedback as necessary and test the plugin whereever possible