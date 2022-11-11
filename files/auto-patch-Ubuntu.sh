#!/bin/bash

# This file is managed by Ansible. See roles/auto_patch/files/auto-patch-Debian.sh

DATE_STAMP=`date +"%Y-%m-%d_%H%M"`

# Ensure running from directory of script
BASEDIR=$(dirname "$0")
cd $BASEDIR

if [[ -e ./pre_update.sh ]]; then
  ./pre_update.sh
fi

echo "auto-patch:" >/var/log/auto-patch/auto-patch-update.${DATE_STAMP} 2>&1
ln -sf /var/log/auto-patch/auto-patch-update.${DATE_STAMP} /var/log/auto-patch/auto-patch-update.latest

/usr/bin/apt-get update
/usr/bin/apt-get -q=2 upgrade >>/var/log/auto-patch/auto-patch-update.${DATE_STAMP} 2>&1

if [[ -e /usr/bin/snap ]]; then
  echo "" >> /var/log/auto-patch-update.out
  echo "snap refresh:" >> /var/log/auto-patch-update.out
  snap refresh >>/var/log/auto-patch-update.out 2>&1
fi

if [[ -e /usr/bin/flatpak ]]; then
  echo "" >> /var/log/auto-patch-update.out
  echo "flatpak update -y:" >> /var/log/auto-patch-update.out
  flatpak update -y >>/var/log/auto-patch-update.out 2>&1
fi


if [[ -e ./post_update.sh ]]; then
  ./post_update.sh
fi

exit 0
