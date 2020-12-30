#!/bin/sh

if [ "`tty`" != "not a tty" ] && [ -e /var/run/reboot-required ]; then
  echo "*** Reboot required ***"
  cat /var/run/reboot-required
fi
