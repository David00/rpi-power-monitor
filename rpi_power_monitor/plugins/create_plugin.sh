#!/usr/bin/env bash

# Author: David00
# Description: This bash script will initialize a barebones plugin template for the Power Monitor for Raspberry Pi Project.
# Usage: If this file is not executable, make it so with: chmod +x create_plugin.sh
#        Then, simply run it with ./create_plugin.sh and provide the name of your new plugin. Do not include any special characters in your plugin name.
#        When complete, you'll have a new folder created in the plugins directory corresponding to your plugin name, along with a README template, and a plugin code template.
# More Info: See the plugin documentation at https://david00.github.io/rpi-power-monitor/docs/v0.3.0/plugins.html

echo "Enter the name of your plugin: "
read -r plugin_name

GREEN='\033[0;32m'
NC='\033[0m'
LRED='\033[1;31m'

# Validate plugin name - Replace all spaces with _
if [[ $plugin_name =~ " " ]]; then
    # Format plugin name to remove spaces
    plugin_name=${plugin_name//" "/"_"}
fi

# Check for special characters
if [[ $plugin_name =~ [\`~!@#$%\^\&\*()=\+\'\"]+ ]]; then
    echo -e "${LRED}There are special characters in your plugin name. The plugin name should only include alphanumeric characters, dashes (-), and underscores (_).${NC}"
    exit
fi

echo "Setting up plugin \"$plugin_name\" in $(pwd)"

mkdir $plugin_name
cp ./plugin_template.py $plugin_name/$plugin_name.py
cp ./README_Template.md $plugin_name/README.md

sed -i "s|plugin_name|${plugin_name^}|g" $plugin_name/$plugin_name.py 
sed -i "s|plugin_name|${plugin_name^}|g" $plugin_name/README.md



echo -e "${GREEN}Done! Created $plugin_name.py and README.md inside plugins/$plugin_name/${NC}"