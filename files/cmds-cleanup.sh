#!/bin/sh

MAX=14
COUNT=0
for cmds_dir in `ls -d /var/log/auto-patch/20[2-9][0-9]-[0-1][1-2]-[0-3][0-9]_* 2>/dev/null | sort -r`; do
  COUNT=$((COUNT+1))
  if [ $COUNT -gt $MAX ]; then
    rm -rf $cmds_dir
    echo "removed ${cmds_dir}"
  fi
done

find /var/log/auto-patch -name 'auto-patch-update.*' -type f -mtime +60 -exec rm -f {} \;

