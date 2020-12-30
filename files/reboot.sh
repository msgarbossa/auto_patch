#!/bin/sh

if [ -e "/var/run/reboot-required" ]; then
    echo "auto-patch: rebooting"
    sync; sync; sync
    sleep 5
    /sbin/reboot
else
    echo "auto-patch: no reboot is required"
fi