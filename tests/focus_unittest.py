import os
import sys
import types
import shutil
import tempfile
import subprocess

IS_MACOSX = sys.platform.lower().startswith('darwin')

# check for unittest
if sys.version_info[:2] < (2, 7):
    try:
        # workaround using unittest2 for python<2.7
        from unittest2 import (
            TestCase, TestLoader, TextTestRunner, skipUnless, skipIf
        )

    except ImportError:
        sys.stderr.write("ERROR: Focus tests require the 'unittest2' package."
                         + os.linesep)
        sys.exit(1)

else:  # 2.7+
    from unittest import (
        TestCase, TestLoader, TextTestRunner, skipUnless, skipIf
    )

# check for psutil
try:
    import psutil
except ImportError:
    sys.stderr.write("ERROR: Focus tests require the 'psutil' package."
                     + os.linesep)
    sys.exit(1)

# check for argparse
try:
    import argparse
except ImportError:
    sys.stderr.write("ERROR: Focus tests require the 'argparse' package."
                     + os.linesep)
    sys.exit(1)

# update sys.path with our lib dir, so libs are available
LIB_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, LIB_DIR)
from focus import errors


__all__ = ('IS_MACOSX', 'skipUnless', 'skipIf', 'TestCase', 'TestLoader',
           'TextTestRunner', 'FocusTestCase', 'MockIOStream', 'MockTask',
           'MockEnvironment')


class FocusTestCase(TestCase):
    def setUp(self):
        super(FocusTestCase, self).setUp()
        self.test_dir = None

    def tearDown(self):
        if self.test_dir:
            self.clean_paths(self.test_dir)
        super(FocusTestCase, self).tearDown()

    def setup_dir(self):
        """ Creates testing directory for use with test case.
            """
        self.test_dir = os.path.realpath(
                            tempfile.mkdtemp(prefix='focus_test_'))

    def make_file(self, data=None):
        """ Writes provided data to a temporary file, relative to temporary
            directory setup by this class.

            `data`
                Data to write to file, defaults to empty string.

            Returns path to temporary file created.
            """

        with tempfile.NamedTemporaryFile('w+b', 0, dir=self.test_dir,
                                         delete=False) as f:
            f.write(data or '')
            return os.path.realpath(f.name)

    def clean_paths(self, *paths):
        """ Removes files or directories without raising.

            `*paths`
                Argument list of paths for files or directories to remove.
            """

        for path in paths:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:  # assume it's a file or link
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def mock_run_root(self, plugin):
        """ Inject `run_root` method into plugin.

            `plugin`
                ``Plugin`` object.
            """
        def run_root(self, command):
            p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            p.communicate()
            return True  # don't check return code.. just lie

        plugin.run_root = types.MethodType(run_root, plugin)


class MockIOStream(object):
    """ Mock object for `IOStream` class.
        """

    def __init__(self):
        self.colored = True

        # patch in the mock methods, each when called will set the
        # associated test__{key}_data attribute on the instance, which can
        # be used to assert when testing usage of the IO's interfaces.
        for k in ('error', 'success', 'write'):
            setattr(self, 'test__{0}_data'.format(k), None)

            # some light meta programming to inject writer methods
            def _wrapper(k):
                def _mockfunc(self, s, newline=True):
                    attrib = 'test__{0}_data'.format(k)
                    value = getattr(self, attrib, None) or ''
                    if newline:
                        s += os.linesep
                    setattr(self, attrib, value + s)
                return _mockfunc
            setattr(self, k, types.MethodType(_wrapper(k), self))

            self.read = types.MethodType(lambda: '', self)

    def set_colored(self, colored):
        self.colored = colored


class MockTask(object):
    """ Mock object for `Task` class.
        """

    def __init__(self, base_dir=None, make_task_dir=False):
        self.name = None
        self._base_dir = base_dir or '/tmp'
        self._task_dir = None

        self._task_dir = os.path.join(self._base_dir, 'tasks', 'test')
        if make_task_dir:
            os.makedirs(self._task_dir)

        self.owner = os.getuid()
        self.duration = 10
        self._total_duration = 0
        self.elapsed = False
        self._loaded = False

    def load(self):
        self._loaded = True
        return True

    def start(self, name):
        if self._loaded:
            raise errors.ActiveTask(self._name)
        self.name = name
        self._loaded = True
        return True

    def stop(self):
        if not self._loaded:
            raise errors.NoActiveTask
        self._loaded = False

    def set_total_duration(self, duration):
        self._total_duration = duration

    def create(self, name, clone_task=None):
        if not hasattr(self, 'test__created'):
            self.test__created = []

        for task_name, _ in self.test__created:
            if task_name == name:
                raise errors.TaskExists(name)

        self.test__created.append((name, clone_task))
        return True

    def exists(self, name):
        try:
            dir_path = os.path.join(self._base_dir, 'tasks', name)
            return os.path.exists(dir_path)

        except OSError:
            return False

    def rename(self, old_name, new_name):
        if not hasattr(self, 'test__renamed'):
            self.test__renamed = {}

        if old_name == new_name:
            raise ValueError

        if not old_name in self.test__renamed:
            raise errors.TaskNotFound(old_name)

        if new_name in self.test__renamed:
            raise errors.TaskExists(new_name)

        self.test__renamed[new_name] = True
        if old_name in self.test__renamed:
            del self.test__renamed[old_name]

        return True

    def remove(self, name):
        try:
            dir_path = os.path.join(self._base_dir, 'tasks', name)
            shutil.rmtree(dir_path)
            return True

        except OSError:
            return False

    def get_config_path(self, name):
        return os.path.join(self._base_dir, 'tasks', name, 'task.cfg')

    def get_list_info(self, task_name=None):
        tasks = [('test1', [('test_opt', ['12345'])], []),
                 ('test2', [('test_opt', ['999'])], [])]

        if task_name:
            tasks = [x for x in tasks if x[0] == task_name]
        return tasks

    @property
    def active(self):
        return self._loaded

    @property
    def base_dir(self):
        return self._base_dir

    @property
    def task_dir(self):
        return self._task_dir


class MockEnvironment(object):
    """ Mock object for `Environment` class.
        """

    def __init__(self, data_dir=None, args=None):
        self.io = MockIOStream()
        self.args = args or []
        self.data_dir = data_dir or '/tmp'
        self.task = MockTask(base_dir = self.data_dir)
        self.loaded = False

    def load(self):
        self.loaded = True


class MockPlugin(object):
    name = 'oh hai'
    version = '1.0'
    target_version = '>=0.1.0'
    command = 'oh_hai'
    events = ['task_start', 'task_run', 'task_end']
    options = [
        {
            'block': 'apps',
            'options': [{'name': 'sup'}]
        }
    ]
    task_only = False

    def deregister(self):
        if not hasattr(self, 'test__deregister'):
            self.test__deregister = 0
        self.test__deregister += 1

    def parse_option(self, option, block, *values):
        if not hasattr(self, 'test__option'):
            self.test__option = []
        self.test__option.append((option, block, values))

    def execute(self, env, args):
        if not hasattr(self, 'test__execute'):
            self.test__execute = []
        self.test__execute.append((env, args))

    def on_taskstart(self, task):
        if not hasattr(self, 'test__task_started'):
            self.test__task_started = 0
        self.test__task_started += 1

    def on_taskrun(self, task):
        if not hasattr(self, 'test__task_ran'):
            self.test__task_ran = 0
        self.test__task_ran += 1

    def on_taskend(self, task):
        if not hasattr(self, 'test__task_ended'):
            self.test__task_ended = 0
        self.test__task_ended += 1
