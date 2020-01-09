# Licensed under a 3-clause BSD style license - see LICENSE.rst
import argparse
from ska_helpers import __version__, run_info   # noqa


def get_opt(args=None):
    """
    Get options for command line interface to update_cmd_states.
    """
    parser = argparse.ArgumentParser(description='test')
    parser.add_argument("--test")
    args = parser.parse_args(args)
    return args


def test_run_info():
    opt = get_opt(['--test', 'value'])
    info = run_info.get_run_info(opt)
    exp = {'filename': __file__,
           'version': __version__,
           # 'time': 'Sun Dec 29 14:15:06 2019',
           # 'user': 'aldcroft',
           # 'machine': 'daze.local',
           'args': {'test': 'value'}}

    for key in exp:
        assert info[key] == exp[key]

    for key in ['time', 'user', 'machine']:
        assert key in info


def test_run_info_lines():
    opt = get_opt(['--test', 'test value!'])
    info_lines = run_info.get_run_info_lines(opt)
    assert f'Running: {__file__}' in info_lines
    assert f'Version: {__version__}' in info_lines
    assert "{'test': 'test value!'}" in info_lines
