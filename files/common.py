#!/usr/bin/env python3

import sys
import os
import logging
import subprocess
import json
import re
import inspect

def setup_logging(log_file=None, log_file_level='debug', log_print_level='info'):

    # Get root logger and setLevel to DEBUG so all messages flow through
    logger_root = logging.getLogger()
    logger_root.setLevel(logging.DEBUG)

    # Create a console handle and set its log level.
    handler_console = logging.StreamHandler()
    handler_console.setLevel(getattr(logging, log_print_level.upper()))
    # set a format which is simpler for console use
    formatter_console = logging.Formatter('%(levelname)-8s %(message)s')
    # tell the handler to use this format
    handler_console.setFormatter(formatter_console)
    # add handler to root logger
    logger_root.addHandler(handler_console)

    # Create a file handler with timestamps and delimiter (:) and set its level.
    if log_file is not None:
        # Make sure logging directory exists
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)

        handler_file = logging.FileHandler(log_file)
        handler_file.setLevel(getattr(logging, log_file_level.upper()))
        # set a format so file contains timestamps and user info
        formatter_file = logging.Formatter('%(levelname)s:%(asctime)s:%(message)s', datefmt='%Y-%m-%d %H.%M.%S %z')
        # tell the handler to use this format
        handler_file.setFormatter(formatter_file)
        # add handler to root logger
        logger_root.addHandler(handler_file)

def get_cmd3(cmd, timeout=None, no_log=False):
    def_name = inspect.currentframe().f_code.co_name
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    try:
        # when Popen's shell argument is True, pid is sthe process ID for the spawned shell instead of child process
        pid = process.pid
        if no_log:
            logging.info('{0}: pid={1}, cmd={2}'.format(def_name, pid, "masked due to no_log=True"))
        else:
            logging.info('{0}: pid={1}, cmd={2}'.format(def_name, pid, cmd))
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        stderr += '\n(timed out after {0} seconds)'.format(timeout)
    retval = process.returncode

    # Logging
    if retval != 0:
        logging.warn('{0}: pid={1}, rc={2}'.format(def_name, pid, retval))
    else:
        logging.debug('{0}: pid={1}, rc={2}'.format(def_name, pid, retval))
    if not no_log:
        if len(stdout) > 0:
            logging.debug('{0}: pid={1}, stdout={2}'.format(def_name, pid, stdout))
        if len(stderr) > 0:
            logging.warn('{0}: pid={1}, stderr={2}'.format(def_name, pid, stderr))
    return retval, stdout, stderr

# realtime (no polling, output to stdout/stderr)
def run_cmd(cmd, no_log=False, timeout=None):
    process = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr, universal_newlines=True)  # noqa: E501
    try:
        # when Popen's shell argument is True, pid is sthe process ID for the spawned shell instead of child process
        pid = process.pid
        if no_log:
            logging.info('run_cmd: pid={0}, cmd={1}'.format(pid, "masked due to no_log=True"))
        else:
            logging.info('run_cmd: pid={0}, cmd={1}'.format(pid, cmd))
        process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        print('timed out after {0} seconds'.format(timeout))
    retval = process.returncode
    if retval != 0:
        logging.warn('run_cmd: pid={0}, rc={1}'.format(pid, retval))
    else:
        logging.debug('run_cmd: pid={0}, rc={1}'.format(pid, retval))
    return retval

# poll every second (may need flush, doesn't implement timeout)
def run_cmd_poll(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, universal_newlines=True)
    # when Popen's shell argument is True, pid is sthe process ID for the spawned shell instead of child process
    pid = process.pid
    logging.info('run_cmd_poll: pid={0}, cmd={1}'.format(pid, cmd))
    while True:
        stdout = process.stdout.readline()
        if stdout == '' and process.poll() is not None:
            break
        if stdout:
            print(stdout.strip())
    retval = process.poll()
    return retval

def get_dict_from_file(input_file):
    if not input_file:
        logging.error('input_file not specified in {0}'.format('get_dict_from_file'))
        sys.exit(1)

    if not os.path.exists(input_file):
        logging.error('{0} not found'.format(input_file))
        sys.exit(1)

    doc = dict()
    # read json
    if re.search(r'\.json', input_file):
        doc = get_dict_from_json_file(input_file)
    else:
        logging.error('Could not determine file type for {0} (should be *.json)'.format(input_file))
        sys.exit(1)

    # sys.exit(0)
    return doc

def get_dict_from_json_file(input_file):

    # Read json from file
    json_string = open(input_file).read()

    # Parse (validate) json
    json_docs = []
    json_docs.append(json.loads(json_string))
    # json_dict = json.loads(json_string)

    # return dict representation
    return json_docs

def get_dict_from_toml_file(input_file):
    # To avoid a dependency on the toml Python module, this def does a simple streaming (line-by-line) read.
    # Does not support advanced TOML, just simple un-nested sections w/ key-value pairs.
    # Comments are stripped out.

    if not os.path.exists(input_file):
        logging.error('{0} not found'.format(input_file))
        sys.exit(1)

    # Initialize variables
    toml_dict = dict()
    section = ""

    # parse ansible.cfg

    # compile regex objects
    # re_comments = re.compile(r"\#.*")
    re_comments = re.compile(r'#.*$')  # same as above, but single quoted
    re_section = re.compile(r"^\[(.*?)\]")

    with open(input_file) as file:
        for line in file:
            line = line.rstrip('\r\n')
            match = re_section.search(line)
            if match:
                section = match.group(1)
                toml_dict[section] = {}
                continue
            line = re_comments.sub('', line)  # remove comments
            kv = line.split('=')
            if len(kv) < 2:
                continue
            k = kv[0]
            v = kv[1]
            k = k.replace(' ', '')  # remove whitespace
            v = v.replace(' ', '')  # remove whitespace
            if k == '':
                continue
            toml_dict[section][k] = v
    return toml_dict

class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values

    Example:
    dict_diff = DictDiffer(dict_current, dict_past)
    print("Added:", dict_diff.added())
    print("Removed:", dict_diff.removed())
    print("Changed:", dict_diff.changed())
    print("Unchanged:", dict_diff.unchanged())
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.current_keys, self.past_keys = [
            set(d.keys()) for d in (current_dict, past_dict)
        ]
        self.intersect = self.current_keys.intersection(self.past_keys)

    def added(self):
        return self.current_keys - self.intersect

    def removed(self):
        return self.past_keys - self.intersect

    def changed(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] != self.current_dict[o])

    def unchanged(self):
        return set(o for o in self.intersect
                   if self.past_dict[o] == self.current_dict[o])
