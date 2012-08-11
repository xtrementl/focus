""" This module provides an encapsulation of the functionality of a task. The
    provided class is used extensively throughout the system to track, load,
    start, and stop a given task, lending to the main functionality of the
    system via plugin delegation and daemons.
    """

import os
import shutil
import datetime

from focus.plugin import registration
from focus import common, errors, daemon, parser


class Task(object):
    """ Class that provides a streamlined interface to task management.
        """

    # header name definitions for config files
    HEADER_ACTIVE_FILE = 'active_task'
    HEADER_TASK_CONFIG = 'task'

    def __init__(self, base_dir):
        """ Initializes class.

            `base_dir`
                Base directory for task data.
            """

        self._name = None
        self._start_time = None
        self._total_duration = 0
        self._owner = os.getuid()
        self._loaded = False
        self._default_task_config = '/etc/focus_task.cfg'

        self._paths = {
            # base working directory
            'base_dir': base_dir,

            # stores info about currently active task
            'active_file': os.path.join(base_dir, '.active.cfg'),

            # base directory for tasks
            'task_dir': None,

            # current task configuration file
            'task_config': None
        }

    def _reset(self):
        """ Resets class properties.
            """

        self._name = None
        self._start_time = None
        self._owner = os.getuid()
        self._paths['task_dir'] = None
        self._paths['task_config'] = None
        self._loaded = False

    def _get_task_dir(self, task_name):
        """ Returns path to task directory for provided task name.

            `task_name`
                Name of task.

            Returns string.
            """
        return os.path.join(self._paths['base_dir'],
                            'tasks', task_name)

    def _save_active_file(self):
        """ Saves current task information to active file.

            Example format::
                active_task {
                    name "task name";
                    start_time "2012-04-23 15:18:22";
                }
            """

        _parser = parser.SettingParser()

        # add name
        _parser.add_option(None, 'name', common.to_utf8(self._name))

        # add start time
        start_time = self._start_time.strftime('%Y-%m-%d %H:%M:%S.%f')
        _parser.add_option(None, 'start_time', start_time)

        # write it to file
        return _parser.write(self._paths['active_file'],
                             self.HEADER_ACTIVE_FILE)

    def _clean_prior(self):
        """ Cleans up from a previous task that didn't exit cleanly.

            Returns ``True`` if previous task was cleaned.
            """

        if self._loaded:
            try:
                pid_file = daemon.get_daemon_pidfile(self)

                # check if it exists so we don't raise
                if os.path.isfile(pid_file):
                    # read pid from file
                    pid = int(common.readfile(pid_file))

                    # check if pid file is stale
                    if pid and not daemon.pid_exists(pid):
                        common.safe_remove_file(pid_file)
                        raise ValueError

            except (ValueError, TypeError):
                self._clean()
                return True

        return False

    def _clean(self):
        """ Cleans up an active task and resets its data.
            """

        common.safe_remove_file(self._paths['active_file'])
        self._reset()

    def load(self):
        """ Loads a task if the active file is available.
            """

        try:
            _parser = parser.parse_config(self._paths['active_file'],
                                          self.HEADER_ACTIVE_FILE)

            # parse expected options into a dict to de-dupe
            keys = ('name', 'start_time')
            opts = dict(o for o in _parser.options if o[0] in keys)

            # check for all keys
            for k in keys:
                if not opts.get(k):
                    return False
            task_name = opts.get('name')[0]

            # setup the paths
            task_dir = self._get_task_dir(task_name)
            task_config = os.path.join(task_dir, 'task.cfg')

            # validate start time
            value = opts.get('start_time')[0]
            start_time = datetime.datetime.strptime(value,
                                                    '%Y-%m-%d %H:%M:%S.%f')

            # get user id for process ownership when running task
            # here, we use the owner of the active file
            file_meta = os.stat(self._paths['active_file'])
            owner = file_meta.st_uid

            # parse task config and send its options to registered plugins
            _parser = parser.parse_config(task_config, self.HEADER_TASK_CONFIG)
            registration.run_option_hooks(_parser)

            self._name = common.from_utf8(task_name)
            self._start_time = start_time
            self._owner = owner
            self._paths['task_dir'] = task_dir
            self._paths['task_config'] = task_config
            self._loaded = True

        except (parser.ParseError, ValueError, TypeError, OSError):
            # something failed, cleanup
            self._clean()

        self._clean_prior()
        return self._loaded

    def exists(self, task_name):
        """ Determines if task directory exists.

            `task_name`
                Task name.

            Returns ``True`` if task exists.
            """

        try:
            return os.path.exists(self._get_task_dir(task_name))

        except OSError:
            return False

    def get_config_path(self, task_name):
        """ Returns path to task configuration file.

            `task_name`
                Task name to get configuration file for.

            Returns string.
            """

        return os.path.join(self._get_task_dir(task_name), 'task.cfg')

    def create(self, task_name, clone_task=None):
        """ Creates a new task directory.

            `task_name`
                Task name.
            `clone_task`
                Existing task name to use as a template for new task.

            Returns boolean.

            * Raises ``Value`` if task name is invalid, ``TaskExists`` if task
              already exists, or ``TaskNotFound`` if task for `clone_from`
              doesn't exist.
            """

        if not task_name or task_name.startswith('-'):
            raise ValueError('Invalid task name')

        try:
            task_dir = self._get_task_dir(task_name)

            if self.exists(task_dir):
                raise errors.TaskExists(task_name)

            task_cfg = self.get_config_path(task_name)

            if clone_task:
                if not self.exists(clone_task):
                    raise errors.TaskNotFound(clone_task)

                # copy task directory
                shutil.copytree(self._get_task_dir(clone_task), task_dir)

            else:
                os.mkdir(task_dir)

                # write default task configuration
                shutil.copy(self._default_task_config, task_cfg)

            return True

        except OSError:
            shutil.rmtree(task_dir, ignore_errors=True)
            return False

    def rename(self, old_task_name, new_task_name):
        """ Renames an existing task directory.

            `old_task_name`
                Current task name.
            `new_task_name`
                New task name.

            Returns ``True`` if rename successful.
            """

        if not old_task_name or old_task_name.startswith('-'):
            raise ValueError('Old task name is invalid')

        if not new_task_name or new_task_name.startswith('-'):
            raise ValueError('New new task name is invalid')

        if old_task_name == new_task_name:
            raise ValueError('Cannot rename task to itself')

        try:
            old_task_dir = self._get_task_dir(old_task_name)
            if not self.exists(old_task_dir):
                raise errors.TaskNotFound(old_task_name)

            new_task_dir = self._get_task_dir(new_task_name)
            if self.exists(new_task_dir):
                raise errors.TaskExists(new_task_name)

            os.rename(old_task_dir, new_task_dir)
            return True

        except OSError:
            return False

    def remove(self, task_name):
        """ Removes an existing task directory.

            `task_name`
                Task name.

            Returns ``True`` if removal successful.
            """

        try:
            task_dir = self._get_task_dir(task_name)
            shutil.rmtree(task_dir)
            return True

        except OSError:
            return False

    def get_list_info(self, task_name=None):
        """ Lists all tasks and associated information.

            `task_name`
                Task name to limit. Default: return all valid tasks.

            Returns list of tuples (task_name, options, block_options)
            """
        try:
            tasks = []

            # get all tasks dirs
            tasks_dir = os.path.join(self._paths['base_dir'], 'tasks')

            if task_name:
                # if task folder doesn't exist, return nothing
                if not os.path.isdir(os.path.join(tasks_dir, task_name)):
                    return []

                task_names = [task_name]

            else:
                task_names = [name for name in os.listdir(tasks_dir)
                              if os.path.isdir(os.path.join(tasks_dir, name))]
                task_names.sort()

            for name in task_names:
                try:
                    # parse task config and run option hooks
                    task_config = os.path.join(tasks_dir, name, 'task.cfg')
                    parser_ = parser.parse_config(task_config,
                                                  self.HEADER_TASK_CONFIG)
                    registration.run_option_hooks(parser_,
                                                  disable_missing=False)

                    tasks.append((name, parser_.options, parser_.blocks))

                except (parser.ParseError, errors.InvalidTaskConfig):
                    tasks.append((name, None, None))

            return tasks

        except OSError:
            return []

    def start(self, task_name):
        """ Starts a new task matching the provided name.

            `task_name`
                Name of existing task to start.

            Returns boolean.

            * Raises a ``TaskNotFound`` exception if task doesn't exist, an
              ``InvalidTaskConfig` exception if task config file is invalid, or
              ``DaemonFailStart`` exception if task daemons failed to fork.
            """

        self._clean_prior()

        if self._loaded:
            raise errors.ActiveTask

        # get paths
        task_dir = os.path.join(self._paths['base_dir'], 'tasks', task_name)
        task_config = os.path.join(task_dir, 'task.cfg')

        if not os.path.isdir(task_dir):
            raise errors.TaskNotFound(task_name)

        try:
            # raise if task config is missing
            if not os.path.isfile(task_config):
                reason = u"Config file could not be found."
                raise errors.InvalidTaskConfig(task_config, reason=reason)

            # parse task config and send its options to registered plugins
            _parser = parser.parse_config(task_config, self.HEADER_TASK_CONFIG)
            registration.run_option_hooks(_parser)

        except parser.ParseError as exc:
            raise errors.InvalidTaskConfig(task_config,
                                           reason=unicode(exc))

        # populate task info
        self._name = common.from_utf8(task_name)
        self._start_time = datetime.datetime.now()
        self._owner = os.getuid()
        self._paths['task_dir'] = task_dir
        self._paths['task_config'] = task_config
        self._loaded = True

        # task is setup, save active file
        # note, order is *important*; this is needed first
        # for the daemon to load
        self._save_active_file()

        # shell the focusd daemon
        try:
            started = daemon.shell_focusd(self._paths['base_dir'])

        # user cancelled or passwords failed?
        except (KeyboardInterrupt, ValueError):
            self._clean()
            return False

        # no event plugins registered, carry on
        except errors.NoPluginsRegistered:
            return True

        # failed, cleanup our mess
        if not started:
            self._clean()
            raise errors.DaemonFailStart

        return True

    def stop(self):
        """ Stops the current task and cleans up, including removing active
            task config file.

            * Raises ``NoActiveTask`` exception if no active task found.
            """

        self._clean_prior()

        if not self._loaded:
            raise errors.NoActiveTask

        self._clean()

    def set_total_duration(self, duration):
        """ Set the total task duration in minutes.
            """
        if duration < 1:
            raise ValueError(u'Duration must be postive')

        elif self.duration > duration:
            raise ValueError(u'{0} must be greater than current duration')

        self._total_duration = duration

    def __str__(self):
        name = common.to_utf8(self.name)
        duration = '<1' if self.duration < 1 else '{0}'.format(self.duration)
        return 'Task (name={0}, duration={1}m)'.format(name, duration)

    def __unicode__(self):
        duration = '<1' if self.duration < 1 else '{0}'.format(self.duration)
        return u'Task (name={0}, duration={1}m)'.format(self.name, duration)

    @property
    def active(self):
        """ Returns if task is active.
            """
        if not os.path.isfile(self._paths['active_file']):
            return False
        return self._loaded

    @property
    def name(self):
        """ Returns task name.
            """
        return self._name or u'<No Name>'

    @property
    def owner(self):
        """ Returns owner user identifier for task.
            """
        return self._owner

    @property
    def duration(self):
        """ Returns task's current duration in minutes.
            """

        if not self._loaded:
            return 0

        delta = datetime.datetime.now() - self._start_time
        total_secs = (delta.microseconds +
                      (delta.seconds + delta.days * 24 * 3600) *
                      10 ** 6) / 10 ** 6

        return max(0, int(round(total_secs / 60.0)))

    @property
    def elapsed(self):
        """ Returns if task's duration has exceeded total_duration value.
            """
        return bool(self._total_duration and
                    self.duration >= self._total_duration)

    @property
    def base_dir(self):
        """ Returns base directory path.
            """
        return self._paths['base_dir']

    @property
    def task_dir(self):
        """ Returns task directory path.
            """
        return self._paths['task_dir']
