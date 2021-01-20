import os
import json

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']
).get_hosts('all')


def test_auto_patch_files_created(host):
    f = host.file('/var/log/auto-patch/current/cmds.json')
    assert f.exists
    assert f.contains("ifconfig")

    f = host.file('/var/log/auto-patch/current/report.json')
    assert f.exists
    assert f.contains("exit")


def test_auto_patch_json_cmds(host):
    s = host.file('/var/log/auto-patch/current/cmds.json').content
    j = json.loads(s)
    assert 'ifconfig -a' in j, f'{"ifconfig -a key not found in /var/log/auto-patch/current/cmds.json"}'  # noqa: E501


def test_auto_patch_json_results(host):
    s = host.file('/var/log/auto-patch/current/report.json').content
    j = json.loads(s)
    assert 'exit' in j, f'{"exit key not found in /var/log/auto-patch/current/report.json"}'  # noqa: E501
    assert j['exit'] == 0, f'{"/var/log/auto-patch/current/report.json should have exit 0 return code"}'  # noqa: E501
