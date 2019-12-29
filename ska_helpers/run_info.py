"""Run time information"""

import time
import platform
import pprint
import inspect
import os

from ska_helpers import __version__  # noqa


def get_run_info(opt=None, version=None, stack_level=1):
    calling_frame_record = inspect.stack()[stack_level]
    calling_func_file = calling_frame_record[1]

    if version is None:
        calling_frame = calling_frame_record[0]
        version = calling_frame.f_globals.get('__version__', 'undefined')

    info = {'filename': calling_func_file,
            'version': version,
            'time': time.ctime(),
            'user': os.getlogin(),
            'machine': platform.node(),
            'args': vars(opt) if hasattr(opt, '__dict__') else opt}
    return info


def get_run_info_string(opt=None, version=None):
    info = get_run_info(opt, version, stack_level=2)
    info_lines = [
        f'******************************************',
        f'Running: {info["filename"]}',
        f'Version: {info["version"]}',
        f'Time: {info["time"]}',
        f'User: {info["user"]}',
        f'Machine: {info["machine"]}',
        f'Processing args:',
        pprint.pformat(info["args"]),
        f'******************************************']
    return os.linesep.join(info_lines)


def test_run_info_string():
    print(get_run_info_string())
