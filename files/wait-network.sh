#!/bin/sh

# This script can be put at ./post-update.d/80-wait-network.sh to wait for the
# tx/rx packet rate to fall below a maximum threshold before continuing with a reboot.
# No action is taken unless /var/run/reboot-required exists.

if [ ! -e "/var/run/reboot-required" ]; then
    echo "auto-patch: skipping network activity check because no reboot is required"
    exit 0
fi

wait_maximum_pps=10

# Get primary interface from default route
if_def=`netstat -rn | grep ^0.0.0.0 | awk '{print $NF}'`

# initialize packet counters
count_rx_curr=`netstat -in | awk -v if_def=$if_def '($1 == if_def) {print $3}'`
count_tx_curr=`netstat -in | awk -v if_def=$if_def '($1 == if_def) {print $7}'`

# initialize pps w/ max_pps so first iteration is skipped
wait_5m_count=$(($wait_maximum_pps * 60 * 5))

# while [ $packet_rx -gt $wait_5m_count ] || [ $packet_tx -gt $wait_5m_count ]; do
while [ true ]; do
  # current values becomes previous
  count_rx_prev=$count_rx_curr
  count_tx_prev=$count_tx_curr
  echo "Waiting for 5m rx/tx packet rate to fall below ${wait_maximum_pps} pps"
  sleep 300
  count_rx_curr=`netstat -in | awk -v if_def=$if_def '($1 == if_def) {print $3}'`
  count_tx_curr=`netstat -in | awk -v if_def=$if_def '($1 == if_def) {print $7}'` 
  packet_rx=$(($count_rx_curr - $count_rx_prev))
  packet_tx=$(($count_tx_curr - $count_tx_prev))
  echo "5m rx packets=${packet_rx}"
  echo "5m tx packets=${packet_tx}"
  if [ $packet_rx -lt $wait_5m_count ] && [ $packet_tx -lt $wait_5m_count ]; then
    break
  fi
done

echo "auto-patch: 5m rx/tx packet rate is below ${wait_maximum_pps} pps (rx count=${packet_rx}, tx count=${packet_tx} < ${wait_5m_count})"
echo "auto-patch: continuing"

exit 0
