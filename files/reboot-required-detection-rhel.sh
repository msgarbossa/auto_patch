#!/bin/bash

# Initialize log file
LOG=/var/log/auto-patch/reboot-required-detection.out
>$LOG

# Get current kernel name
CURRENT_KERNEL="$(rpm -q kernel-$(uname -r))"
if [ -z "$CURRENT_KERNEL" ]; then
  echo "Current kernel is a custom kernel" | tee -a $LOG
  # exit 0
fi

# Get latest kernel name
LATEST_KERNEL="$(rpm -q kernel | tail -1)"
if [ -z "$LATEST_KERNEL" ]; then
  echo "No kernel package installed.  Maybe rpm is broken." | tee -a $LOG
  exit 1
fi

# Get boot time
BOOTTIME="$(sed -n '/^btime /s///p' /proc/stat)"
if [ -z "$BOOTTIME" ]; then
  echo "Error reading BOOTTIME" | tee -a $LOG
  exit 1
fi

# Get latest kernel install time
LATEST_KERNEL_INSTALLTIME=$(rpm -q kernel --qf "%{INSTALLTIME}\n" | sort -n | tail -1)
if [ -z "$LATEST_KERNEL_INSTALLTIME" ]; then
  echo "Error reading kernel INSTALLTIME" | tee -a $LOG
  exit 1
fi

# Compare current/latest kernel names.  If no match, check boot/install time.
if [ "$CURRENT_KERNEL" = "$LATEST_KERNEL" ]; then
  echo "Latest kernel running, no reboot needed" | tee -a $LOG
else
  if [ "$LATEST_KERNEL_INSTALLTIME" -lt "$BOOTTIME" ]; then
    echo "Latest kernel not running, but system was restarted already." | tee -a $LOG
    echo "User switched back to an old kernel?" | tee -a $LOG
  elif [ "$LATEST_KERNEL_INSTALLTIME" -gt "$BOOTTIME" ]; then
    echo "Latest kernel not running.  Reboot needed." | tee -a $LOG
    echo "Updating /var/run/reboot-required" | tee -a $LOG
    grep "[KERNEL]" /var/run/reboot-required >/dev/null 2>&1 ||
      echo `date`: [KERNEL] new kernel $LATEST_KERNEL installed, but server has not been rebooted >> /var/run/reboot-required
  fi
fi

# Get glibc install time
GLIBC_INSTALLTIME=$(rpm -q glibc --qf "%{INSTALLTIME}\n" | sort -n | tail -1)
if [ -z "$GLIBC_INSTALLTIME" ]; then
  echo "Error reading glibc INSTALLTIME" | tee -a $LOG
  exit 1
fi

if [ "$GLIBC_INSTALLTIME" -gt "$BOOTTIME" ]; then
  echo "glibc was updated.  Reboot needed." | tee -a $LOG
  echo "Updating /var/run/reboot-required" | tee -a $LOG
  # TODO: Only append if equivelent entry doesn't already exist (grep first)
  grep "[GLIBC]" /var/run/reboot-required >/dev/null 2>&1 ||
    echo `date`: [GLIBC] new glibc installed, but server has not been rebooted >> /var/run/reboot-required
fi
