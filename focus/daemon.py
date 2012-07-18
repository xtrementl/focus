""" This module manages the daemon for plugin and task needs.

    It provides interfaces to shell the focusd daemon, the command server, and
    task runner processes.
    """

import os
import sys
import pwd
import grp
import time
import errno
import types
import signal
import atexit
import multiprocessing

from focus import errors, common
from focus.plugin import registration

__all__ = ('get_daemon_pidfile', 'pid_exists', 'daemonize', 'shell_focusd',
           'focusd', 'Focusd', 'TaskRunner', 'CommandServer')


def _shutdown_pipe(pipe):
    """ Sends the sentinel shutdown value through the provided full-duplex
        (socket-pair) pipe and closes either end of the pipe.

        `pipe`
            ``multiprocessing.Pipe`` full-duplex object.
        """

    for end in pipe:
        try:
            end.send_bytes('TRM')
            end.close()

        except IOError:
            pass


def get_daemon_pidfile(task):
    """ Get path for focusd daemon pid file.

        `task`
            ``Task`` instance.

        Returns filename string.
        """

    return os.path.join(task.base_dir, '.focusd.pid')


def pid_exists(pid):
    """ Determines if a system process identifer exists in process table.
        """
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    else:
        return True


def daemonize(pid_file, working_dir, func):
    """ Turns the current process into a daemon.

        `pid_file`
            File path to use as pid lock file for daemon.
        `working_dir`
            Working directory to switch to when daemon starts.
        `func`
            Callable to run after daemon is forked.
        """

    def _fork():
        """ Fork a child process.

            Returns ``False`` if fork failed; otherwise,
            we are inside the new child process.
            """
        try:
            pid = os.fork()
            if pid > 0:
                os._exit(0)  # exit parent
            return True

        except OSError:
            return False

    def _register_pidfile(filename):
        """ Registers a pid file for the current process which will cleaned up
            when the process terminates.

            `filename`
                Filename to save pid to.
            """
        if common.writefile(filename, str(os.getpid()) + os.linesep):
            os.chmod(filename, 0644)  # rw-r--r--

            def _cleanup_pid():
                """ Removes pidfile.
                    """
                common.safe_remove_file(filename)
            atexit.register(_cleanup_pid)

    if not pid_file or not working_dir or not func:
        return

    if not os.path.isfile(pid_file):  # enforce pid lock file
        # attempt first fork
        if not _fork():
            return

        try:
            # detach from current environment
            os.chdir(working_dir)
            os.setsid()
            os.umask(0)

        except OSError:
            return

        # attempt second fork
        if not _fork():
            return

        # we'll ignore closing file descriptors..
        # redirecting the streams should be sufficient

        # redirect streams to /dev/null
        _fd = os.open(os.devnull, os.O_RDWR)
        os.dup2(_fd, sys.stdin.fileno())
        os.dup2(_fd, sys.stdout.fileno())
        os.dup2(_fd, sys.stderr.fileno())

        # setup pidfile
        _register_pidfile(pid_file)

        # execute provided callable
        func()


def shell_focusd(data_dir):
    """ Shells a new instance of a focusd daemon process.

        `data_dir`
            Home directory for focusd data.

        Returns boolean.

        * Raises ``ValueError`` if sudo used and all passwords tries failed.
        """

    command = 'focusd {0}'.format(data_dir)

    # see what event hook plugins are registered
    plugins = registration.get_registered(event_hooks=True)

    if not plugins:  # none registered, bail
        raise errors.NoPluginsRegistered

    # do any of the plugins need root access?
    # if so, wrap command with sudo to escalate privs, if not already root
    needs_root = any(p for p in plugins if p.needs_root)

    if needs_root and os.getuid() != 0:  # only if not already root
        command = 'sudo ' + command
    else:
        needs_root = False

    # shell the daemon process
    _, code = common.shell_process(command, exitcode=True)

    if code == 1 and needs_root:  # passwords failed?
        raise ValueError

    return code == 0


def focusd(task):
    """ Forks the current process as a daemon to run a task.

        `task`
            ``Task`` instance for the task to run.
        """

    # determine if command server should be started
    if registration.get_registered(event_hooks=True, root_access=True):
        # root event plugins available
        start_cmd_srv = (os.getuid() == 0)  # must be root
    else:
        start_cmd_srv = False

    # daemonize our current process
    _run = lambda: Focusd(task).run(start_cmd_srv)
    daemonize(get_daemon_pidfile(task), task.task_dir, _run)


class Focusd(object):
    """ Defines the container for the Focus daemon process.

        `task`
            ``Task`` object.
        """

    def __init__(self, task):
        self._exited = False
        self._pidfile = get_daemon_pidfile(task)
        self._task = task
        self._pipe = multiprocessing.Pipe(duplex=True)
        self._sleep_period = 1.0  # one second

        # child procs
        pid = os.getpid()
        self._task_runner = TaskRunner(task, pid, self._pipe)
        self._command_server = CommandServer(task, pid, self._pipe)

    def _reg_sighandlers(self):
        """ Registers signal handlers to this class.
            """

        # SIGCHLD, so we shutdown when any of the child processes exit
        _handler = lambda signo, frame: self.shutdown()
        signal.signal(signal.SIGCHLD, _handler)
        signal.signal(signal.SIGTERM, _handler)

    def _drop_privs(self):
        """ Reduces effective privileges for this process to that of the task
            owner. The umask and environment variables are also modified to
            recreate the environment of the user.
            """

        uid = self._task.owner

        # get pwd database info for task owner
        try:
            pwd_info = pwd.getpwuid(uid)

        except OSError:
            pwd_info = None

        # set secondary group ids for user, must come first
        if pwd_info:
            try:
                gids = [g.gr_gid for g in grp.getgrall()
                        if pwd_info.pw_name in g.gr_mem]
                gids.append(pwd_info.pw_gid)
                os.setgroups(gids)

            except OSError:
                pass

            # set group id, must come before uid
            try:
                os.setgid(pwd_info.pw_gid)
            except OSError:
                pass

        # set user id
        try:
            os.setuid(uid)

            # update user env variables
            if pwd_info:
                for k in ('USER', 'USERNAME', 'SHELL', 'HOME'):
                    if k in os.environ:
                        if k in ('USER', 'USERNAME'):
                            val = pwd_info.pw_name

                        elif k == 'SHELL':
                            val = pwd_info.pw_shell

                        elif k == 'HOME':
                            val = pwd_info.pw_dir

                        # update value
                        os.environ[k] = val

            # remove unneeded env variables
            keys = []
            for k, _ in os.environ.iteritems():
                if k.startswith('SUDO_') or k == 'LOGNAME':
                    keys.append(k)
            for k in keys:
                del os.environ[k]

        except OSError:
            pass

        # set default umask
        try:
            os.umask(022)
        except OSError:
            pass

    def shutdown(self):
        """ Shuts down the daemon process.
            """

        if not self._exited:
            self._exited = True

            # signal task runner to terminate via SIGTERM
            if self._task_runner.is_alive():
                self._task_runner.terminate()

                # if command server is running, then block until
                # task runner completes so it has time to use
                # the command server to clean up root plugins
                if self._command_server.is_alive():
                    if self._task_runner.is_alive():
                        self._task_runner.join()

            _shutdown_pipe(self._pipe)
            self._task.stop()

    def run(self, start_command_srv):
        """ Setup daemon process, start child forks, and sleep until
            events are signalled.

            `start_command_srv`
                Set to ``True`` if command server should be started.
            """

        if start_command_srv:
            # note, this must be established *before* the task runner is forked
            # so the task runner can communicate with the command server.

            # fork the command server
            self._command_server.start()

            # drop root privileges; command server will remain as the only
            # daemon process with root privileges. while root plugins have root
            # shell access, they are known and the commands are logged by the
            # command server.
            self._drop_privs()

        # fork the task runner
        self._task_runner.start()

        # setup signal handlers
        self._reg_sighandlers()

        while self.running:
            time.sleep(self._sleep_period)

        self.shutdown()

    @property
    def running(self):
        """ Determines if daemon is active.

            Returns boolean.
            """

        # check if task is active and pid file exists
        return (not self._exited and os.path.isfile(self._pidfile)
                and self._task.active)


class TaskProcess(multiprocessing.Process):
    """ Defines the container process that handles running tasks.

        `task`
            ``Task`` object.
        `parent_pid`
            Process identifier for calling process.
        `pipe`
            ``multiprocessing.Pipe`` duplex socket-pair object.
        """

    def __init__(self, task, parent_pid, pipe):
        super(TaskProcess, self).__init__()

        self._exited = False
        self._task = task
        self._pipe = pipe
        self._ppid = parent_pid
        self._sleep_period = 0.1  # 1/10 second

    def _register_sigterm(self):
        """ Registers SIGTERM signal handler.
            """

        _handler = lambda signo, frame: self.shutdown()
        signal.signal(signal.SIGTERM, _handler)

    def _prepare(self):
        """ Setup initial requirements for daemon run.
            """
        self._register_sigterm()

    def _run(self):
        """ Override this for running during the main event loop.

            Return ``False`` to end the main event loop.
            """
        pass

    def run(self):
        """ Main process loop.
            """

        self._prepare()

        while self.running:
            if self._run() is False:
                break
            time.sleep(self._sleep_period)

        self.shutdown()

    def shutdown(self):
        """ Shuts down the process.
            """

        if not self._exited:
            self._exited = True
            _shutdown_pipe(self._pipe)
            self._task.stop()
            raise SystemExit

    @property
    def running(self):
        """ Determines if process is active.

            Returns boolean.
            """

        # check if parent process is still alive
        return not self._exited and pid_exists(self._ppid)


class TaskRunner(TaskProcess):
    """ Task Runner process: runs event plugins while a task is active.
        """

    def __init__(self, *args, **kwargs):
        super(TaskRunner, self).__init__(*args, **kwargs)
        self._cmd_pipe = self._pipe[0]
        self._rlock = multiprocessing.RLock()
        self._sleep_period = 1.0  # one second

        self._ran_taskstart = False

    def _setup_root_plugins(self):
        """ Injects a `run_root` method into the registered root event plugins.
            """

        def run_root(_self, command):
            """ Executes a shell command as root.

                `command`
                    Shell command string.

                Returns boolean.
                """

            try:
                # get lock, so this plugin has exclusive access to command pipe
                self._rlock.acquire()

                # TODO: log root command for this plugin
                self._cmd_pipe.send_bytes('\x80'.join(['SHL', command]))
                res = self._cmd_pipe.recv_bytes()

                if res != 'TRM':  # sentinel value, shutdown
                    return res == 'OK'

            except (EOFError, IOError):
                pass

            finally:
                self._rlock.release()

            self.shutdown(skip_hooks=True)
            return False

        # inject method into each event plugin
        for plugin in registration.get_registered(event_hooks=True,
                                                  root_access=True):
            plugin.run_root = types.MethodType(run_root, plugin)

    def _run_events(self, shutdown=False):
        """ Runs event hooks for registered event plugins.

            `shutdown`
                Set to ``True`` to run task_end events;
                otherwise, run task_run events.
            """

        # run task_start events, if not ran already
        if not self._ran_taskstart:
            self._ran_taskstart = True
            registration.run_event_hooks('task_start', self._task)

        # run events
        event = 'task_end' if shutdown else 'task_run'
        registration.run_event_hooks(event, self._task)

        # reclaim any subprocesses plugins may have forked
        try:
            os.waitpid(-1, os.P_NOWAIT)
        except OSError:
            pass

    def _prepare(self):
        """ Setup initial requirements for daemon run.
            """

        super(TaskRunner, self)._prepare()
        self._setup_root_plugins()

        # set the default x-window display for non-mac systems
        if not sys.platform.lower().startswith('darwin'):
            if not 'DISPLAY' in os.environ:
                os.environ['DISPLAY'] = ':0.0'

    def _run(self):
        """ Runs events for plugins during the main process loop.
            """

        if self._task.elapsed:
            self.shutdown()

        else:
            self._run_events()

    def shutdown(self, skip_hooks=False):
        """ Shuts down the process.

            `skip_hooks`
                Set to ``True`` to skip running task end event plugins.
            """

        if not self._exited:
            self._exited = True

            if not skip_hooks:
                self._run_events(shutdown=True)

            _shutdown_pipe(self._pipe)
            self._task.stop()
            raise SystemExit


class CommandServer(TaskProcess):
    """ Command Server process: executes shell commands for event plugins while
        a task is active.
        """

    def __init__(self, *args, **kwargs):
        super(CommandServer, self).__init__(*args, **kwargs)
        self._cmd_pipe = self._pipe[1]

    def _process_commands(self):
        """ Processes commands received and executes them accordingly.
            Returns ``True`` if successful, ``False`` if connection closed or
            server terminated.
            """

        try:
            # poll for data, so we don't block forever
            if self._cmd_pipe.poll(1):  # 1 sec timeout
                payload = self._cmd_pipe.recv_bytes()

                if payload:
                    # segment payload
                    parts = payload.split('\x80', 2)
                    _op = parts[0]

                    # terminate operation
                    if _op == 'TRM':
                        raise EOFError

                    # shell command operation
                    elif _op == 'SHL' and len(parts) == 2:
                        command = parts[1]

                        if command:
                            # run command and return success or fail
                            res = common.shell_process(command)

                            if res is not None:
                                self._cmd_pipe.send_bytes('OK')
                                return True

                    # everything else, should reply with "FAIL"
                    self._cmd_pipe.send_bytes('FAIL')

        except (EOFError, IOError):
            return False

        else:
            return True

    def _prepare(self):
        """ Setup initial requirements for daemon run.
            """

        super(CommandServer, self)._prepare()

        # unregister all active plugins
        for plugin in registration.get_registered():
            registration.disable_plugin_instance(plugin)

    def _run(self):
        """ Processes commands received during main process loop.

            Returns boolean.
            """

        return self._process_commands()
