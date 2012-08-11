""" This module provides the application-specific task plugins that implement
    the 'apps' settings block in the task configuration file.

    Features supported include::
        - Starting applications at task start.
        - Closing applications at task start.
        - Blocking applications during an active task.
    """

import os
import time
import psutil
import hashlib

from focus import common
from focus.plugin import base

__all__ = ('AppRun', 'AppClose', 'AppBlock')


_process_checksums = {}  # cache for `_stop_processes`


def _get_process_cwd(pid):
    """ Returns the working directory for the provided process identifier.

        `pid`
            System process identifier.

        Returns string or ``None``.

        Note this is used as a workaround, since `psutil` isn't consistent on
        being able to provide this path in all cases, especially MacOS X.
        """

    cmd = 'lsof -a -p {0} -d cwd -Fn'.format(pid)

    data = common.shell_process(cmd)

    if not data is None:
        lines = str(data).split('\n')

        # the cwd is the second line with 'n' prefix removed from value
        if len(lines) > 1:
            return lines[1][1:] or None

    return None


def _get_checksum(path):
    """ Generates a md5 checksum of the file at the specified path.

        `path`
            Path to file for checksum.

        Returns string or ``None``
        """

    # md5 uses a 512-bit digest blocks, let's scale by defined block_size
    _md5 = hashlib.md5()
    chunk_size = 128 * _md5.block_size

    try:
        with open(path, 'rb') as _file:
            for chunk in iter(lambda: _file.read(chunk_size), ''):
                _md5.update(chunk)
        return _md5.hexdigest()

    except IOError:
        return None


def _get_user_processes():
    """ Gets process information owned by the current user.

        Returns generator of tuples: (``psutil.Process`` instance, path).
        """

    uid = os.getuid()

    for proc in psutil.process_iter():
        try:
            # yield processes that match current user
            if proc.uids.real == uid:
                yield (proc, proc.exe)

        except psutil.AccessDenied:
            # work around for suid/sguid processes and MacOS X restrictions
            try:
                path = common.which(proc.name)

                # psutil doesn't support MacOS X relative paths,
                # let's use a workaround to merge working directory with
                # process relative path
                if not path and common.IS_MACOSX:
                    cwd = _get_process_cwd(proc.pid)
                    if not cwd:
                        continue
                    path = os.path.join(cwd, proc.cmdline[0])

                yield (proc, path)

            except (psutil.AccessDenied, OSError):
                pass

        except psutil.NoSuchProcess:
            pass


def _stop_processes(paths):
    """ Scans process list trying to terminate processes matching paths
        specified. Uses checksums to identify processes that are duplicates of
        those specified to terminate.

        `paths`
            List of full paths to executables for processes to terminate.
        """

    def cache_checksum(path):
        """ Checksum provided path, cache, and return value.
            """
        if not path:
            return None

        if not path in _process_checksums:
            checksum = _get_checksum(path)
            _process_checksums[path] = checksum

        return _process_checksums[path]

    if not paths:
        return

    target_checksums = dict((cache_checksum(p), 1) for p in paths)
    if not target_checksums:
        return

    for proc, path in _get_user_processes():
        # path's checksum matches targets, attempt to terminate
        if cache_checksum(path) in target_checksums:
            try:
                proc.terminate()

            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass


class AppRun(base.Plugin):
    """ Runs applications at task start and completion.
        """
    name = 'AppRun'
    version = 0.1
    target_version = '>=0.1'
    events = ['task_start', 'task_end']
    options = [
        # Example:
        #   apps {
        #       run firefox, chromium;
        #       run "echo hi >> /tmp/foo.bar";
        #       run "whoami >> /tmp/whoami";
        #       run chromium\ http://www.google.com;
        #       end_run killall\ urxvt;
        #       timer_run killall\ urxvt;
        #   }

        {
            'block': 'apps',
            'options': [
                {'name': 'run'},
                {'name': 'end_run'},
                {'name': 'timer_run'}
            ]
        }
    ]

    def __init__(self):
        super(AppRun, self).__init__()
        self.paths = {}

    def _run_apps(self, paths):
        """ Runs apps for the provided paths.
            """

        for path in paths:
            common.shell_process(path, background=True)
            time.sleep(0.2)  # delay some between starts

    def parse_option(self, option, block_name, *values):
        """ Parse app path values for option.
            """
        if option == 'run':
            option = 'start_' + option

        key = option.split('_', 1)[0]
        self.paths[key] = set(common.extract_app_paths(values))

    def on_taskstart(self, task):
        if 'start' in self.paths:
            self._run_apps(self.paths['start'])

    def on_taskend(self, task):
        key = 'timer' if task.elapsed else 'end'
        paths = self.paths.get(key)

        if paths:
            self._run_apps(paths)


class AppClose(base.Plugin):
    """ Closes applications at task start and completion.
        """
    name = 'AppClose'
    version = '0.1'
    target_version = '>=0.1'
    events = ['task_start', 'task_end']
    options = [
        # Example:
        #   apps {
        #       close firefox, chromium;
        #       close /usr/bin/something;
        #       end_close urxvt;
        #       timer_close urxvt;
        #   }

        {
            'block': 'apps',
            'options': [
                {'name': 'close'},
                {'name': 'end_close'},
                {'name': 'timer_close'}
            ]
        }
    ]

    def __init__(self):
        super(AppClose, self).__init__()
        self.paths = {}

    def parse_option(self, option, block_name, *values):
        """ Parse app path values for option.
            """

        # treat arguments as part of the program name (support spaces in name)
        values = [x.replace(' ', '\\ ') if not x.startswith(os.sep) else x
                  for x in [str(v) for v in values]]

        if option == 'close':
            option = 'start_' + option

        key = option.split('_', 1)[0]
        self.paths[key] = set(common.extract_app_paths(values))

    def on_taskstart(self, task):
        if 'start' in self.paths:
            _stop_processes(paths=self.paths['start'])

    def on_taskend(self, task):
        key = 'timer' if task.elapsed else 'end'
        paths = self.paths.get(key)

        if paths:
            _stop_processes(paths=paths)


class AppBlock(AppClose):
    """ Blocks applications during an active task.
        """
    name = 'AppBlock'
    version = '0.1'
    target_version = '>=0.1'
    events = ['task_run']
    options = [
        # Example:
        #   apps {
        #       block firefox, chromium;
        #       block /usr/bin/something;
        #       block '/path/to/bin/';
        #   }

        {
            'block': 'apps',
            'options': [
                {'name': 'block'}
            ]
        }
    ]

    def on_taskrun(self, task):
        _stop_processes(paths=self.paths['block'])
