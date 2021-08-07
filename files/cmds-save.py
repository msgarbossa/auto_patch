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

# Initialize arg_dict
arg_dict = dict()
cmds_dict = dict()

# Help message
def usage(exit_code=0):
    """ Display help message if -h option used or invalid syntax. """
    print(os.path.basename(__file__) + ' [-o <save_file.json>] [-v ] [-l <log_file>]')
    print("\t-l\tlog file for commands (default /var/log/auto-patch/current/cmds.log)")
    print("\t-o\tJSON file to save command output to (default /var/log/auto-patch/current/cmds.json)")
    print("\t-v\tverbose output")
    sys.exit(exit_code)

def parse_args(arg_dict):
    # Parse CLI input #
    try:
        opts, _args = getopt.getopt(sys.argv[1:], "hvl:o:", ["help"])
    except getopt.GetoptError as err:
        logging.error(err)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-v':
            arg_dict['verbose'] = True
        elif opt == '-l':
            arg_dict['log_file'] = arg
        elif opt == '-o':
            arg_dict['save_file'] = arg
        elif opt == '-h':
            arg_dict['usage'] = True
        elif opt == '--help':
            arg_dict['usage'] = True
    return arg_dict

def save_cmd_to_dict(cmd, timeout=None, key=None):
    rc, stdout, stderr = get_cmd3(cmd, timeout=timeout)
    if key == None:
        key = cmd
    cmds_dict[key] = {}
    if key != cmd:
        cmds_dict[key]['cmd'] = cmd
    cmds_dict[key]['stdout'] = stdout
    cmds_dict[key]['stderr'] = stderr
    cmds_dict[key]['rc'] = rc

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

    output_text = json.dumps(cmds_dict, indent=4)

    # write output to specified file
    fh = open(cmd_out_file, "w")
    fh.write(output_text)
    fh.close()
    os.chmod(cmd_out_file, 0o600)


if __name__ == '__main__':

    # default configuration options
    arg_dict['usage'] = False
    arg_dict['verbose'] = False

    # call function to parse CLI arguments to override defaults
    arg_dict = parse_args(arg_dict)

    if arg_dict['usage']:
        usage(2)

    arg_dict['data_dir'] = '/var/log/auto-patch'

    # Setup logging options based on verbose setting
    if arg_dict['verbose']:
        setup_logging(log_file='./debug.out', log_file_level='debug', log_print_level='info')
    else:
        setup_logging(log_file=None, log_file_level='info', log_print_level='warn')

    if 'save_file' not in arg_dict:

        # Create data directory if it doesn't exist
        if not os.path.exists(arg_dict['data_dir']):
            os.makedirs(arg_dict['data_dir'])

        # Change current working directory to data directory so paths are relative
        os.chdir(arg_dict['data_dir'])

        # Remove previous "current" directory and link to new data-stamped directory
        if os.path.exists("current"):
            os.remove("current")

        # Create directory with date-stamp and symlink current to new directory
        datetime = strftime("%Y-%m-%d_%H%M%S", localtime())
        # date_dir = os.path.join(arg_dict['data_dir'], datetime)
        date_dir = datetime
        os.makedirs(date_dir)
        ln_src = os.path.join(arg_dict['data_dir'], "current")
        os.symlink(datetime, ln_src)
        arg_dict['save_file'] = os.path.join(arg_dict['data_dir'], 'current', 'cmds.json')

    collect_cmds()

    save_cmd_dict_to_file(arg_dict['save_file'])
