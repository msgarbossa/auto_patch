#!/bin/sh

# Ensure running from directory of script
BASEDIR=$(dirname "$0")
cd $BASEDIR

# Track exit code and change to 1 if any script fails (but run all scripts)
exit_code=0

# If post_update.d directory exists, look to see if any scripts are executable and run them
if [ -d "./post_update.d" ]; then
    for i in `ls ./post_update.d/* 2>/dev/null | sort`; do
        if [ -d $i ]; then
          continue
        fi
        if [ -x "$i" ]; then
            echo "Running ${i}"
            ./${i}
            if [ $? -ne 0 ]; then
              echo "${i} returned non-zero return code"
              exit_code=1
            fi
        fi
    done
else
    # Create post_update.d directory if it doesn't exist
    mkdir -m 700 ./post_update.d
fi

exit $exit_code
