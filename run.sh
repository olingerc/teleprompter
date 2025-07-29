#!/bin/bash

# Autostart on Raspian OS
# sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
# add line there:
# @/home/chris/workspace/teleprompter/run.sh

script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
parentdir="$(dirname "$script_dir")"

# Git pull songbook
echo "Pulling new songbooks in SONGBOOK in ${parentdir}/songbooks"
cd "${parentdir}/songbooks"
git pull

# Git pull app and run
echo "Starting Telepromter in ${script_dir}"
cd "${script_dir}"
git pull
$script_dir/.venv/bin/python3 $script_dir/main.py
