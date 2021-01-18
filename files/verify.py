#!/usr/bin/env python3

import sys
import os
import shutil
import subprocess
import json
from time import time, localtime, strftime
import getopt

from common import *

####################
# Global variables #
####################

# Initialize dictionaries
arg_dict = dict()
cmds_dict_curr = dict()
cmds_dict_prev = dict()
report_dict = dict()

# Help message
def usage(exit_code=0):
    """ Display help message if -h option used or invalid syntax. """
    print(os.path.basename(__file__) + ' [-i <cmd_file.json>] [-o <out_file.json>] [-v] [-l <log_file>]')
    print("\t-l\tlog file for report (default /var/log/auto-patch/current/report.log)")
    print("\t-i\tJSON file to read command output from (default /var/log/auto-patch/current/cmds.json)")
    print("\t-o\tJSON file to write report to (default report.json in directory for -i)")
    print("\t-v\tverbose output")
    sys.exit(exit_code)

def parse_args(arg_dict):
    # Parse CLI input #
    try:
        opts, _args = getopt.getopt(sys.argv[1:], "hvl:i:o:", ["help"])
    except getopt.GetoptError as err:
        logging.error(err)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-v':
            arg_dict['verbose'] = True
        elif opt == '-l':
            arg_dict['log_file'] = arg
        elif opt == '-i':
            arg_dict['save_file'] = arg
        elif opt == '-o':
            arg_dict['report_file'] = arg
        elif opt == '-h':
            arg_dict['usage'] = True
        elif opt == '--help':
            arg_dict['usage'] = True
    return arg_dict

def save_cmd_to_dict(cmd, timeout=None, key=None):
    rc, stdout, stderr = get_cmd3(cmd, timeout=timeout)
    if key == None:
        key = cmd
    cmds_dict_curr[key] = {}
    if key != cmd:
        cmds_dict_curr[key]['cmd'] = cmd
    cmds_dict_curr[key]['stdout'] = stdout
    cmds_dict_curr[key]['stderr'] = stderr
    cmds_dict_curr[key]['rc'] = rc

def collect_cmds():
    save_cmd_to_dict("date +\"%Y-%m-%d %H:%M:%S\"")
    save_cmd_to_dict("date +\"%s\"")
    save_cmd_to_dict('uname')
    # save_cmd_to_dict("echo \$TZ")
    save_cmd_to_dict('uptime')
    save_cmd_to_dict('netstat -rn')
    save_cmd_to_dict('/sbin/ifconfig -a', key='ifconfig -a')
    save_cmd_to_dict('cat /proc/swaps')
    save_cmd_to_dict('df -k', timeout=15)
    save_cmd_to_dict('mount')
    save_cmd_to_dict('cat /etc/resolv.conf')
    # save_cmd_to_dict('ntpq -pn')
    if os.path.exists('/usr/bin/dpkg'):
        save_cmd_to_dict('dpkg --list')
    if os.path.exists('/usr/bin/rpm'):
        save_cmd_to_dict("rpm -qa --queryformat=\"%{NAME}:%{VERSION}\\n\"", key='rpm_custom')
    save_cmd_to_dict('netstat -an')
    save_cmd_to_dict("ps -www -eo \"pmem pcpu time vsz rss user pid args\"", key='ps_custom')
    save_cmd_to_dict('cat /etc/ssh/sshd_config')

def save_cmd_dict_to_file(cmd_out_file):

    output_text = json.dumps(cmds_dict_curr, indent=4)

    # write output to specified file
    fh = open(cmd_out_file, "w")
    fh.write(output_text)
    fh.close()
    os.chmod(cmd_out_file, 0o600)

def validate_ifconfig():

    cmd_key = 'ifconfig -a'
    results = {}
    results[cmd_key] = {}
    results[cmd_key]['status'] = 'success'
    results[cmd_key]['msgs'] = []

    if cmd_key not in cmds_dict_prev:
        results[cmd_key]['msgs'].append('{0}: not found in previous command output'.format(cmd_key))
        results[cmd_key]['status'] = 'failed'
        return results

    if cmd_key not in cmds_dict_curr:
        results[cmd_key]['msgs'].append('{0}: not found in current command output'.format(cmd_key))
        results[cmd_key]['status'] = 'failed'
        return results

    # Variables and regex for parsing command output
    re_interface = re.compile(r'(^\S.*?)\s')
    interfaces_prev = {}
    interfaces_curr = {}
    re_ip1 = re.compile(r'inet addr:(.*?)\s')
    re_ip2 = re.compile(r'inet (.*?)\s')

    # Parse previous info
    for line in cmds_dict_prev[cmd_key]['stdout'].split('\n'):
        line = line.rstrip()

        # Find each interface
        m = re_interface.search(line)
        if m:
            interface = m.group(1)
            interface = interface.replace(':', '')  # remove colon
            interfaces_prev[interface] = []

        # Check for IP using 2 patterns (covers multiple Operating Systems)
        m = re_ip1.search(line)
        if m:
            ip = m.group(1)
            interfaces_prev[interface].append(ip)
        else:
            m = re_ip2.search(line)
            if m:
                ip = m.group(1)
                interfaces_prev[interface].append(ip)

    # Parse current info
    for line in cmds_dict_curr[cmd_key]['stdout'].split('\n'):
        line = line.rstrip()

        # Find each interface
        m = re_interface.search(line)
        if m:
            interface = m.group(1)
            interface = interface.replace(':', '')  # remove colon
            interfaces_curr[interface] = []

        # Check for IP using 2 patterns (covers multiple Operating Systems)
        m = re_ip1.search(line)
        if m:
            ip = m.group(1)
            interfaces_curr[interface].append(ip)
        else:
            m = re_ip2.search(line)
            if m:
                ip = m.group(1)
                interfaces_curr[interface].append(ip)

    # Compare previous and current
    d = DictDiffer(interfaces_curr, interfaces_prev)
    if len(d.added()) > 0:
        results[cmd_key]['msgs'].append('added: ' + ', '.join(d.added()))
        results[cmd_key]['status'] = 'failed'

    if len(d.removed()) > 0:
        results[cmd_key]['msgs'].append('removed: ' + ', '.join(d.removed()))
        results[cmd_key]['status'] = 'failed'

    if len(d.changed()) > 0:
        results[cmd_key]['msgs'].append('changed: ' + ', '.join(d.changed()))
        results[cmd_key]['status'] = 'failed'

    return results

def validate_fs_mounts():

    cmd_key = 'mount'
    results = {}
    results[cmd_key] = {}
    results[cmd_key]['status'] = 'success'
    results[cmd_key]['msgs'] = []

    if cmd_key not in cmds_dict_prev:
        results[cmd_key]['msgs'].append('{0}: not found in previous command output'.format(cmd_key))
        results[cmd_key]['status'] = 'failed'
        return results

    if cmd_key not in cmds_dict_curr:
        results[cmd_key]['msgs'].append('{0}: not found in current command output'.format(cmd_key))
        results[cmd_key]['status'] = 'failed'
        return results

    # Only check specific filesystem types
    fs_types = {"ext2", "ext3", "ext4", "xfs", "nfs", "nfs3", "nfs4", "gpfs"}

    # Capture mount order to check for overmounted filesystems
    mount_order = []

    # Variables and regex for parsing command output
    mps_prev = {}
    mps_curr = {}

    # Parse previous info
    for line in cmds_dict_prev[cmd_key]['stdout'].split('\n'):
        fields = line.rstrip().split()
        if len(fields) > 0:
            dev, _on, mp, _type, fs_type, options = fields
            # Skip if fs_type isn't one we're interested in
            if fs_type not in fs_types:
                continue
            mps_prev[mp] = {'dev': dev, 'type': fs_type, 'options': options}

    # Parse current info
    for line in cmds_dict_curr[cmd_key]['stdout'].split('\n'):
        fields = line.rstrip().split()
        if len(fields) > 0:
            dev, _on, mp, _type, fs_type, options = fields
            # Skip if fs_type isn't one we're interested in
            if fs_type not in fs_types:
                continue
            mps_curr[mp] = {'dev': dev, 'type': fs_type, 'options': options}
            mount_order.append(mp)  # capture mount order to check for overmounts

    # Compare previous and current
    d = DictDiffer(mps_curr, mps_prev)
    if len(d.added()) > 0:
        results[cmd_key]['msgs'].append('added: ' + ', '.join(d.added()))
        results[cmd_key]['status'] = 'failed'

    if len(d.removed()) > 0:
        results[cmd_key]['msgs'].append('removed: ' + ', '.join(d.removed()))
        results[cmd_key]['status'] = 'failed'

    if len(d.changed()) > 0:
        results[cmd_key]['msgs'].append('changed: ' + ', '.join(d.changed()))
        results[cmd_key]['status'] = 'failed'

    # Check mount order to see that each mounted fs with "/" appended does not match (regex/begin) a previously mounted fs
    mps_checked = []  # initialize empty list to store mounts as they are checked against prior mounts
    print_heading = True
    for mp_curr in mount_order:
        for mp_check in mps_checked:
            mp_curr_slash = '{0}/'.format(mp_check)
            if re.match(mp_curr_slash, mp_check):
                if print_heading:
                    results[cmd_key]['msgs'].append('mount order problems:')
                    results[cmd_key]['status'] = 'failed'
                    print_heading = False
                results[cmd_key]['msgs'].append('{0}: is set to mount before {1}'.format(mp_curr, mp_check))
        mps_checked.append(mp_curr)
    mps_checked = []  # done with this

    return results

def validate_packages():

    results = {}

    # Check dpkg (if exists)
    cmd_key = 'dpkg --list'
    if cmd_key in cmds_dict_curr:
        results[cmd_key] = {}
        results[cmd_key]['status'] = 'success'
        results[cmd_key]['msgs'] = []

        # Parse current info
        if len(cmds_dict_curr[cmd_key]['stderr']) > 0:
            results[cmd_key]['msgs'].append('stderr was returned')
            results[cmd_key]['status'] = 'failed'

    # Check rpm (if exists)
    cmd_key = 'rpm_custom'
    if cmd_key in cmds_dict_curr:
        results[cmd_key] = {}
        results[cmd_key]['status'] = 'success'
        results[cmd_key]['msgs'] = []

        # Parse current info
        if len(cmds_dict_curr[cmd_key]['stderr']) > 0:
            results[cmd_key]['msgs'].append('stderr was returned')
            results[cmd_key]['status'] = 'failed'

            # Check for RPM DB corrupt message in stderr
            re_rpm_corrupt = re.compile(r'DB_RUNRECOVERY')
            m = re_rpm_corrupt.search(cmds_dict_curr[cmd_key]['stderr'])
            if m:
                results[cmd_key]['msgs'].append('RPM database is corrupt')

    return results

def validate_paging_space():

    cmd_key = 'cat /proc/swaps'
    results = {}
    results[cmd_key] = {}
    results[cmd_key]['status'] = 'success'
    results[cmd_key]['msgs'] = []

    if cmd_key not in cmds_dict_prev:
        results[cmd_key]['msgs'].append('{0}: not found in previous command output'.format(cmd_key))
        results[cmd_key]['status'] = 'failed'
        return results

    if cmd_key not in cmds_dict_curr:
        results[cmd_key]['msgs'].append('{0}: not found in current command output'.format(cmd_key))
        results[cmd_key]['status'] = 'failed'
        return results

    # Variables and regex for parsing command output
    re_heading = re.compile(r'^File')
    swaps_prev = {}
    swaps_curr = {}

    # Parse previous info
    for line in cmds_dict_prev[cmd_key]['stdout'].split('\n'):
        line = line.rstrip()

        # Find each swap
        m = re_heading.search(line)
        if m:
            continue
        swap_info = line.split()
        if len(swap_info) > 2:  # Check number of fields because last line is blank
            swaps_prev[swap_info[0]] = swap_info[2]

    # Parse current info
    for line in cmds_dict_curr[cmd_key]['stdout'].split('\n'):
        line = line.rstrip()

        # Find each swap
        m = re_heading.search(line)
        if m:
            continue
        swap_info = line.split()
        if len(swap_info) > 2:  # Check number of fields because last line is blank
            swaps_curr[swap_info[0]] = swap_info[2]

    # Compare previous and current
    d = DictDiffer(swaps_curr, swaps_prev)
    if len(d.added()) > 0:
        results[cmd_key]['msgs'].append('added: ' + ', '.join(d.added()))
        results[cmd_key]['status'] = 'failed'

    if len(d.removed()) > 0:
        results[cmd_key]['msgs'].append('removed: ' + ', '.join(d.removed()))
        results[cmd_key]['status'] = 'failed'

    if len(d.changed()) > 0:
        results[cmd_key]['msgs'].append('changed: ' + ', '.join(d.changed()))
        results[cmd_key]['status'] = 'failed'

    return results


def process_report(report_dict):
    rc = 0
    if arg_dict['verbose']:
        print(json.dumps(report_dict, indent=4))
        print()
    for cmd_key in report_dict.keys():
        if report_dict[cmd_key]['status'] != 'success':
            rc = 1
            logging.error(report_dict[cmd_key])
    report_dict['exit'] = rc

    if rc == 0:
        print('validation=success')
    else:
        print('validation=failed')

    output_text = json.dumps(report_dict, indent=4)

    # write output to specified file
    fh = open(arg_dict['report_file'], "w")
    fh.write(output_text)
    fh.close()
    os.chmod(arg_dict['report_file'], 0o600)

    return rc

if __name__ == '__main__':

    # default configuration options that can be overwritten by CLI
    arg_dict['usage'] = False
    arg_dict['verbose'] = False

    # call function to parse CLI arguments to override defaults
    arg_dict = parse_args(arg_dict)

    if arg_dict['usage']:
        usage(2)

    # Default data directory for input/output files
    arg_dict['data_dir'] = '/var/log/auto-patch'

    # default configurations to set if not set in CLI
    if 'save_file' not in arg_dict:
        arg_dict['save_file'] = os.path.join(arg_dict['data_dir'], 'current', 'cmds.json')

    # default to write report to report.json in the same directory as the input file
    if 'report_file' not in arg_dict:
        arg_dict['report_file'] = os.path.join(os.path.dirname(arg_dict['save_file']), 'report.json')

    # Setup logging options based on verbose setting
    if arg_dict['verbose']:
        if 'log_file not in arg_dict':
            arg_dict['log_file'] = os.path.join(os.path.dirname(arg_dict['report_file']), 'debug.out')
        setup_logging(log_file=arg_dict['log_file'], log_file_level='debug', log_print_level='info')
    else:
        setup_logging(log_file=None, log_file_level='info', log_print_level='warn')

    cmds_dict_prev = get_dict_from_file(arg_dict['save_file'])[0]
    collect_cmds()

    # Update report dictionary with results from validation functions
    report_dict.update(validate_ifconfig())
    report_dict.update(validate_paging_space())
    report_dict.update(validate_packages())
    report_dict.update(validate_fs_mounts())

    # Process report (print errors via logger, save report, determine return code)
    rc = process_report(report_dict)
    sys.exit(rc)
