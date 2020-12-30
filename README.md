# Ansible Role: auto_patch

Sets up cron-based OS auto-patching for Debian-based or RPM-based Linux distributions (Ubuntu/Debian, Redhat).  

- The hour and minute fields of the cron entry are idempotent and generated from a hash of the hostname within specified ranges
- Automatic reboots are enabled by default, which will trigger a reboot if /var/run/reboot-required exists (custom script used for RPM-based Linux distributions to detect kernel changes).
- The auto_reboot role variable can be used to disable automatic reboots, which is useful in a Kubernetes cluster when using a tool such as kured for orchestrating zero downtime VM reboots (kured watches for /var/run/reboot-required to cordon, drain nodes, and perform rolling reboots of the cluster).
- The verify script performs tests such as ensuring previously mounted filesystems are mounted and network interfaces and IPs have not changed.

## Requirements

- /etc/cron.d (cronie package on RHEL or cron package on Ubuntu, which is installed if missing as part of state=enable)

## Role Variables

| Variable         | Choices/Defaults | Purpose/Description                                                                                  |
| ---------------- | ---------------- | ---------------------------------------------------------------------------------------------------- |
| state</br>*string* | **enable**, disable, absent | enable sets up all files and cron entry, disable removes the cron entry, absent removes all associated files |
| script_dir</br>*string* | **/etc/auto-patch** | directory for auto-patch scripts |
| validation</br>*string*| **enable**, disable, absent | enable sets up systemd service, disable removes the service, absent removes all validation-related files |
| auto_reboot</br>*string* | **enable**, disable | automatically reboot after updates are applied if /var/run/reboot-required exists (creates \<script_dir\>/post_update.d/99-reboot.sh) |
| cron_min_min</br>*integer* | **1** | minimum minute for randomly generated cron minute |
| cron_min_max</br>*integer* | **59** | maximum minute for randomly generated cron minute |
| cron_hr_min</br>*integer* | **3** | minimum hour for randomly generated cron hour |
| cron_hr_max</br>*integer* | **5** | maximum hour for randomly generated cron hour |
| cron_day_of_month</br>*string* | **\*** | day of month field in cron entry|
| cron_month</br>*string* | **\*** | month field in cron entry |
| cron_day_of_week</br>*string* | **6-7** | day of week field in cron entry (0-7 where 0 and 7 = Sunday) |

## Role Dependencies

- none

## Directory Structure

- auto-patch scripts are setup in /etc/auto-patch
- \*.d directories handle events and run executable scripts in alphabetical order
- /etc/cron.d/auto-patch controls the schedule for running pre_update.sh, apply updates, and post_update.sh
- The pre_update.d directory contains scripts to cleanup logs and save command output to /var/log/auto-patch/\<datetime_stamp\>
- The post_update.d directory optionally contains the reboot script that checks for /var/run/reboot-required
- /etc/systemd/verify-reboot.service unit file runs post_reboot.sh
- The post_reboot.d directory contains the verification script, which reads previous command output from /var/log/auto-patch/\<datetime_stamp\>/cmds.json
- The verify script writes results to report.json
- /var/log/auto-patch/current/report.json can be read by other tools to determine the results of the validation ("exit" key/value pair in JSON)

```
/
├── /etc
│   ├── /auto-patch
│   │   ├── auto-patch.sh
│   │   ├── /post_reboot.d
│   │   │   ├── 10-verify.py
│   │   │   └── common.py
│   │   ├── post_reboot.sh
│   │   ├── /post_update.d
│   │   │   └── 99-reboot.sh
│   │   ├── post_update.sh
│   │   ├── /pre_update.d
│   │   │   ├── 10-cmds-cleanup.sh
│   │   │   ├── 10-cmds-save.py
│   │   │   └── common.py
│   │   ├── pre_update.sh
│   │   └── verify-reboot.sh
│   ├── /cron.d
│   │   └── auto-patch
│   └── /systemd/system
│       └── verify-reboot.service
└── /var/log/auto-patch
    ├── /<datetime_stamp>
    │   ├── cmds.json
    │   └── report.json
    ├── current -> <datetime_stamp>
    └── cron.out
```

## Example Playbook Tasks

Minimum facts will automatically be gathered if ansible_system is not defined

Basic auto-patch w/ automatic reboots

```yaml
  - name: Setup and enable auto-patch
    include_role:
      name: auto_patch
```

auto-patch w/ automatic reboots disabled and daily OS updates

```yaml
  - name: Setup and enable auto-patch
    include_role:
      name: auto_patch
    vars:
      auto_reboot: disable
      cron_day_of_week: "*"

```

Disable and remove auto-patch

```yaml
  - name: Disable and remove auto-patch and all associated files
    include_role:
      name: auto_patch
    vars:
      state: absent
```

## Testing

Test command-save script:

```bash
root@host:/root# cd /etc/auto-patch/pre_update.d/
root@host:/etc/auto-patch/pre_update.d# ./10-cmds-save.py 
root@host:/etc/auto-patch/pre_update.d# ls -l /var/log/auto-patch/current/
total 120
-rw------- 1 root root 122773 Dec 29 20:38 cmds.json
```

Test verify script (be sure cmds.json exists from above):

```bash
root@host:/root# cd /etc/auto-patch/post_reboot.d/
root@host:/etc/auto-patch/post_reboot.d# ./10-verify.py 
validation=success
root@host:/etc/auto-patch/post_reboot.d# cat /var/log/auto-patch/current/report.json
{
    "ifconfig -a": {
        "status": "success",
        "msgs": []
    },
    "cat /proc/swaps": {
        "status": "success",
        "msgs": []
    },
    "dpkg --list": {
        "status": "success",
        "msgs": []
    },
    "mount": {
        "status": "success",
        "msgs": []
    },
    "exit": 0
```

Test auto-patch process by running command in cron entry (can trigger reboot if reboot is required and enabled after patching)

```bash
root@host:/root# /etc/auto-patch/auto-patch.sh
```

## Future Improvements

- Validation script
  - check NTP sync
  - check systemd services started successfully (analyze chain)
- Configuration file
  - ignore specified validations
  - specify number of validation directories to keep in cleanup script

## License

MIT / BSD

