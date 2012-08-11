""" This package encapsulates the runtime environment, including pathing, the
    current ``Task`` and ``IOStream`` instances, and command-line and daemon
    interfaces to drive the system.
    """

import os
import re
import sys

from focus import errors
from focus.task import Task
from focus.environment.cli import CLI
from focus.environment.io import IOStream

__all__ = ('Environment', 'CLI', 'IOStream')


_RE_PY_EXT = re.compile(r'\.py[co]?$')
_RE_INIT_PY = re.compile(r'__init__\.py[co]?$')


def _import_modules(dir_path):
    """ Attempts to import modules in the specified directory path.

        `dir_path`
            Base directory path to attempt to import modules.
        """

    def _import_module(module):
        """ Imports the specified module.
            """
        # already loaded, skip
        if module in mods_loaded:
            return False

        __import__(module)
        mods_loaded.append(module)

    mods_loaded = []

    # check if provided path exists
    if not os.path.isdir(dir_path):
        return

    try:
        # update import search path
        sys.path.insert(0, dir_path)

        # check for modules in the dir path
        for entry in os.listdir(dir_path):
            path = os.path.join(dir_path, entry)

            if os.path.isdir(path):  # directory
                _import_module(entry)

            elif _RE_PY_EXT.search(entry):  # python file
                if not _RE_INIT_PY.match(entry):  # exclude init
                    name = _RE_PY_EXT.sub('', entry)
                    _import_module(name)
    finally:
        # remove inserted path
        sys.path.pop(0)


class Environment(object):
    """ Basic container for a runtime environment.
        """

    DEF_DATA_DIR = '~/.focus'               # default path for data dir
    DATA_SUBDIRS = ('tasks', 'plugins')     # subdirectories within data dir

    def __init__(self, **kwargs):
        """ Initializes environment.

            `args`
                List of environment arguments. Default: ``None``
            `io`
                IO object for data streams. Default: ``None``
            `data_dir`
                Home directory for focus user data. Default: ~/.focus or value
                defined in $FOCUS_HOME env var.
            `task`
                ``Task`` instance. Default: ``None``
            """

        # argument list
        self._args = kwargs.get('args', list())

        # io stream
        self._io = kwargs.get('io', IOStream())

        # path to focus user data directory (for config files, plugins, etc.)
        #   first: check provided arg, then: $FOCUS_HOME env variable,
        #   finally: use default user homedir path
        self._data_dir = (
            kwargs.get('data_dir') or os.environ.get('FOCUS_HOME') or
            os.path.expanduser(self.DEF_DATA_DIR)  # ~/.focus
        )
        self._data_dir = os.path.realpath(self._data_dir)

        self._task = kwargs.get('task')
        self._loaded = False

    def _setup_directories(self):
        """ Creates data directory structure.

            * Raises a ``DirectorySetupFail`` exception if error occurs
              while creating directories.
            """
        dirs = [self._data_dir]
        dirs += [os.path.join(self._data_dir, name) for name
                 in self.DATA_SUBDIRS]

        for path in dirs:
            if not os.path.isdir(path):
                try:
                    os.makedirs(path)  # recursive mkdir
                    os.chmod(path, 0755)  # rwxr-xr-x

                except OSError:
                    raise errors.DirectorySetupFail()

        return True

    def _setup_task(self, load):
        """ Sets up the ``Task`` object and loads active file for task.

            `load`
                Set to ``True`` to load task after setup.
            """

        if not self._task:
            self._task = Task(self._data_dir)

        if load:
            self._task.load()

    def _load_plugins(self):
        """ Attempts to load plugin modules according to the order of available
            plugin directories.
            """

        # import base plugin modules
        try:
            __import__('focus.plugin.modules')
            #import focus.plugin.modules
        except ImportError as exc:
            raise errors.PluginImport(unicode(exc))

        # load user defined plugin modules
        try:
            user_plugin_dir = os.path.join(self._data_dir, 'plugins')
            _import_modules(user_plugin_dir)

        except Exception as exc:
            raise errors.UserPluginImport(unicode(exc))

    def load(self):
        """ Loads in resources needed for this environment, including loading a
            new or existing task, establishing directory structures, and
            importing plugin modules.
            """

        self._setup_directories()
        self._load_plugins()
        self._setup_task(load=True)
        self._loaded = True

    @property
    def loaded(self):
        """ Returns if environment is loaded.
            """
        return self._loaded

    @property
    def args(self):
        """ Returns original arguments passed into environment.
            """
        return self._args

    @property
    def io(self):
        """ Returns ``IO`` object for environment.
            """
        return self._io

    @property
    def data_dir(self):
        """ Returns data directory path.
            """
        return self._data_dir

    @property
    def task(self):
        """ Returns task associated with environment.
            """
        return self._task
