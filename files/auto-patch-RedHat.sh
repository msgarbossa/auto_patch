#!/bin/bash

# This file is managed by Ansible. See roles/auto_patch/files/auto-patch-RedHat.sh

# DATE_STAMP=`date +"%Y-%m-%d_%H%M"`

# Ensure running from directory of script
BASEDIR=$(dirname "$0")
cd $BASEDIR

if [[ -e ./pre_update.sh ]]; then
  ./pre_update.sh
fi

/usr/bin/yum -y -e 0 update >/var/log/auto-patch/current/auto-patch-update.out 2>&1
# /usr/bin/yum -y -e 0 update >/var/log/auto-patch/auto-patch-update.${DATE_STAMP} 2>&1
# ln -sf /var/log/auto-patch/auto-patch-update.${DATE_STAMP} /var/log/auto-patch/auto-patch-update.latest

if [[ -e ./post_update.sh ]]; then
  ./post_update.sh
fi

exit 0