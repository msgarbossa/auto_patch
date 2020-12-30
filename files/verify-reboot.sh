#!/bin/sh

LOG="/var/log/auto-patch/verify-reboot.out"
echo `date` > $LOG

start() {
  # if do_verify is set, do verification
  do_verify=0

  # Check that command output exists prior to reboot
  cmds_file="/var/log/auto-patch/current/cmds.json"
  if [ ! -f $cmds_file ]; then
    echo "$cmds_file not found: verification will not continue" | tee -a $LOG
    RETVAL=1; return 1
  fi

  # Find time of last patching in epoch seconds from patching log file
  patch_secs=0
  patch_file="/var/log/auto-patch/auto-patch-update.latest"
  if [ -e $patch_file ]; then
    patch_sec_current=$(stat -c "%Y" $patch_file)
    [ $patch_sec_current -gt $patch_secs ] && patch_secs=$patch_sec_current
  fi

  # Find time of last verify in epoch seconds from last validation report
  verify_secs=0
  report_file="/var/log/auto-patch/current/report.json"
  if [ -e $report_file ]; then
    verify_secs=$(stat -c "%Y" $report_file)
  fi

  # do verification if last verify was done before patching
  [ $verify_secs -lt $patch_secs ] && do_verify=1

  if [ $do_verify != 1 ]; then
    echo "Verification has already been done since last patching.  Verification will not continue." | tee -a $LOG
    RETVAL=0; return 0
  fi

  # Ensure running from directory of script
  BASEDIR=$(dirname "$0")
  cd $BASEDIR

  if [ \( ! -L /var/log/auto-patch/current \) -o \( ! -e /var/log/auto-patch/current/cmds.json \) ]; then
    echo "Pre-requisite scripts for automatic validation not found." | tee -a $LOG
    RETVAL=1; return 1
  fi

  # sleep minimum of 30s to allow other processes to start
  sleep_sec=$(awk -v min=30 -v max=60 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
  echo "Sleeping $sleep_sec, collect commands, comparing to pre-reboot state" | tee -a $LOG
  cd /tmp
  CMD="/bin/sleep $sleep_sec && $BASEDIR/post_reboot.sh"
  echo $CMD | tee -a $LOG
  /usr/bin/nohup sh -c "$CMD" </dev/null >>$LOG 2>&1 &
  RETVAL=0
}

status() {
  if [ -e /var/run/reboot-required ]; then
    echo "/var/run/reboot-required exists" | tee -a $LOG
  else
    echo "/var/run/reboot-required not found" | tee -a $LOG
  fi
  RETVAL=0
}

# See how we were called.
case "$1" in
    start)
        start
        ;;
    status)
        status
        ;;
    *)
        echo $"Usage: $0 {start|status}" | tee -a $LOG
        exit 2
esac

exit $RETVAL
