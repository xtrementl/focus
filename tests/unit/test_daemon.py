import os
import pwd
import types

from focus import daemon
from focus.plugin import registration
from focus_unittest import FocusTestCase, MockTask, MockPlugin


def _check_pipe_shutdown(test_case, pipe):
    for end in pipe:
        test_case.assertEqual(end.recv_bytes(), 'TRM')

    test_case.assertTrue(hasattr(pipe, 'test__closed'))


class MockPipe(object):
    def __init__(self):
        self._data = []

    def __getitem__(self, item):
        if item in range(2):
            return self
        raise IndexError

    def send_bytes(self, s):
        self._data.append(s)

    def recv_bytes(self):
        try:
            return self._data.pop(0)

        except IndexError:
            return ''

    def poll(self, timeout):
        return bool(self._data)

    def close(self):
        self.test__closed = True


class MockTaskProcess(object):
    def __init__(self):
        self.alive = False

    def is_alive(self):
        return self.alive

    def start(self):
        if self.alive:
            raise Exception('Cannot start task process multiple times')
        self.alive = True
        self.test__started = True

    def terminate(self):
        if not self.alive:
            raise Exception('Task process already terminated')
        self.alive = False
        self.test__terminated = True

    def join(self):
        if not self.alive:
            raise Exception('Task process cannot be joined if not alive')
        self.test__joined = True


class TestDaemon(FocusTestCase):
    def test___shutdown_pipe(self):
        """ daemon._shutdown_pipe: pipe was successfully shutdown.
            """
        pipe = MockPipe()
        daemon._shutdown_pipe(pipe)
        _check_pipe_shutdown(self, pipe)

    def test__get_daemon_pidfile(self):
        """ daemon.get_daemon_pidfile: returns correct pid file for task.
            """
        task = MockTask()
        filename = os.path.join(task.base_dir, '.focusd.pid')
        self.assertEqual(daemon.get_daemon_pidfile(task), filename)

    def test__pid_exists(self):
        """ daemon.pid_exists: determines if process exists for pid.
            """
        self.assertTrue(daemon.pid_exists(1))  # valid.. let's assume 1 exists
        self.assertFalse(daemon.pid_exists(99999999))  # invalid


class TestFocusd(FocusTestCase):
    def setUp(self):
        super(TestFocusd, self).setUp()
        self.task = MockTask()
        self.pid_file = os.path.join(self.task.base_dir, '.focusd.pid')
        open(self.pid_file, 'w', 0).write('99999999\n')

        self.task.load()
        self.pipe = MockPipe()
        self.focusd = daemon.Focusd(self.task)
        self.focusd._pipe = self.pipe
        self.focusd._command_server = MockTaskProcess()
        self.focusd._task_runner = MockTaskProcess()

    def tearDown(self):
        self.focusd = None
        self.task = None
        self.pipe = None
        self.clean_paths(self.pid_file)

        super(TestFocusd, self).tearDown()

    def _setup_for_run(self):
        # overwrite methods to test if they were called
        def _drop_privs(self):
            self.test__dropped_privs = True
        self.focusd._drop_privs = types.MethodType(_drop_privs, self.focusd)

        def _shutdown(self):
            self.test__shutdown = True
        self.focusd.shutdown = types.MethodType(_shutdown, self.focusd)

        # inject no-op method, we don't want signal handling while testing
        self.focusd._reg_sighandlers = types.MethodType(lambda self: None,
                                                        self.focusd)

    def test___drop_privs(self):
        """ Focusd._drop_privs: privileges are dropped to current user and
            environment variables are updated.
            """

        self.focusd._drop_privs()
        self.assertEqual(self.task.owner, os.getuid())

        # env vars updated
        info = pwd.getpwuid(self.task.owner)
        for k in ('USER', 'USERNAME', 'SHELL', 'HOME'):
            if k in os.environ:
                v = os.environ[k]

                if k in ('USER', 'USERNAME'):
                    self.assertEqual(v, info.pw_name)

                elif k == 'SHELL':
                    self.assertEqual(v, info.pw_shell)

                elif k == 'HOME':
                    self.assertEqual(v, info.pw_dir)

        # some env vars removed
        self.assertEqual([], [k for k in os.environ.keys() if
                               k.startswith('SUDO_') or k == 'LOGNAME'])

        # proper umask set
        try:
            old_mask = os.umask(022)
            os.umask(old_mask)
            self.assertEqual(old_mask, 022)

        except OSError:
            pass

    def test__shutdown(self):
        """ Focusd.shutdown: task runner process is shutdown.
            """
        self.focusd._exited = False
        self.focusd._task_runner.start()
        self.focusd.shutdown()

        _check_pipe_shutdown(self, self.pipe)
        self.assertFalse(self.task.active)

    def testStartCmdServer__run(self):
        """ Focusd.run: run with command server started.
            """
        self._setup_for_run()

        self.focusd._exited = True  # fake it, so event loop stops
        self.focusd.run(start_command_srv=True)

        # all called
        self.assertTrue(hasattr(self.focusd._command_server, 'test__started'))
        self.assertTrue(hasattr(self.focusd, 'test__dropped_privs'))
        self.assertTrue(hasattr(self.focusd._task_runner, 'test__started'))
        self.assertTrue(hasattr(self.focusd, 'test__shutdown'))

    def testWithoutStartCmdServer__run(self):
        """ Focusd.run: run without command server started.
            """
        self._setup_for_run()

        self.focusd._exited = True  # fake it, so event loop stops
        self.focusd.run(start_command_srv=False)

        # not called
        self.assertFalse(hasattr(self.focusd._command_server, 'test__started'))
        self.assertFalse(hasattr(self.focusd, 'test__dropped_privs'))

        # called
        self.assertTrue(hasattr(self.focusd._task_runner, 'test__started'))
        self.assertTrue(hasattr(self.focusd, 'test__shutdown'))

    def testPidFileExistTaskActive__running(self):
        """ Focusd.running (property): pidfile exists and task active: running.
            """
        self.assertTrue(self.focusd.running)

    def testNoPidFileExist__running(self):
        """ Focusd.running (property): no pid file exists: not running.
            """
        self.clean_paths(self.pid_file)
        self.assertFalse(self.focusd.running)

    def testTaskNotActive__running(self):
        """ Focusd.running (property): no active task: not running.
            """
        self.task._loaded = False
        self.assertFalse(self.focusd.running)

    def testExited__running(self):
        """ Focusd.running (property): focusd has exited: not running.
            """
        self.focusd._exited = True
        self.assertFalse(self.focusd.running)


class TestTaskProcess(FocusTestCase):
    def setUp(self):
        super(TestTaskProcess, self).setUp()
        self.task = MockTask()
        self.task.load()
        self.pipe = MockPipe()
        self.process = daemon.TaskProcess(self.task, os.getpid(), self.pipe)

    def tearDown(self):
        self.process = None
        self.pipe = None
        self.task = None
        super(TestTaskProcess, self).tearDown()

    def testExited__running(self):
        """ TaskProcess.running (property): process has exited: not running.
            """
        self.process._exited = True
        self.assertFalse(self.process.running)

    def testParentExited__running(self):
        """ TaskProcess.running (property): parent has exited: not running.
            """
        self.process._ppid = 999999  # set parent pid invalid
        self.assertFalse(self.process.running)

    def test__shutdown(self):
        """ TaskProcess.shutdown: process is shutdown.
            """
        with self.assertRaises(SystemExit):
            self.process.shutdown()
        _check_pipe_shutdown(self, self.pipe)
        self.assertFalse(self.task.active)


class TestTaskRunner(FocusTestCase):
    class MockLock(object):
        def acquire(self):
            pass

        def release(self):
            pass

    def setUp(self):
        super(TestTaskRunner, self).setUp()
        self.task = MockTask()
        self.task.load()
        self.pipe = MockPipe()
        self.task_runner = daemon.TaskRunner(self.task,
                                             os.getpid(),
                                             self.pipe)
        self.task_runner._rlock = self.MockLock()

        # fake event plugin registration
        self.plugin = MockPlugin()
        self.plugin.needs_root = True
        for event in ('task_start', 'task_run', 'task_end'):
            registration._event_hooks[event] = [
                (self.plugin.name, lambda: self.plugin)
            ]

        registration._registered.register(self.plugin.name,
                                          lambda: self.plugin,
                                          {'event': True})

    def tearDown(self):
        self.plugin = None
        self.task_runner = None
        self.pipe = None
        self.task = None

        # unregister
        registration._event_hooks = {}
        registration._registered.clear()

        super(TestTaskRunner, self).tearDown()

    def testElapsedShutdown___run(self):
        """ TaskRunner._run: Shuts down if task has elapsed.
            """
        self.task_runner._task.elapsed = True
        with self.assertRaises(SystemExit):
            self.task_runner._run()

    def test___setup_root_plugins(self):
        """ TaskRunner._setup_root_plugins: installs root plugin methods.
            """
        self.task_runner._setup_root_plugins()

        # setup properly
        method = getattr(self.plugin, 'run_root', None)
        self.assertIsNotNone(method)
        self.assertTrue(callable(method))

        # send command, received "OK" from server
        self.pipe.send_bytes('OK')  # fake response from command server
        self.assertTrue(self.plugin.run_root('omg-llama'))

        # verify packet that was sent to command server
        self.assertEqual(self.pipe.recv_bytes(), 'SHL\x80omg-llama')

        # send again, this time with "FAIL" sent from server
        self.pipe.send_bytes('FAIL')
        self.assertFalse(self.plugin.run_root('omg-llama'))
        self.assertEqual(self.pipe.recv_bytes(), 'SHL\x80omg-llama')

        # test TRM sentinel value received, shuts down this process
        self.pipe.send_bytes('TRM')
        with self.assertRaises(SystemExit):
            self.plugin.run_root('omg-llama')

    def testTaskEnd___run_events(self):
        """ TaskRunner._run_events: runs task_end events.
            """
        self.task_runner._run_events(shutdown=True)
        self.assertTrue(hasattr(self.plugin, 'test__task_started'))
        self.assertTrue(hasattr(self.plugin, 'test__task_ended'))
        self.assertFalse(hasattr(self.plugin, 'test__task_ran'))

    def testTaskRun___run_events(self):
        """ TaskRunner._run_events: runs task_run events.
            """
        self.task_runner._run_events(shutdown=False)
        self.assertTrue(hasattr(self.plugin, 'test__task_started'))
        self.assertTrue(hasattr(self.plugin, 'test__task_ran'))
        self.assertFalse(hasattr(self.plugin, 'test__task_ended'))

        # test running non-shutdown multiple times, should call task_run
        # multiple times
        for i in range(10):
            self.assertEqual(self.plugin.test__task_ran, i + 1)
            self.task_runner._run_events(shutdown=False)

    def testSkipHooks__shutdown(self):
        """ TaskRunner.shutdown: shuts down process, skipping event hooks.
            """
        with self.assertRaises(SystemExit):
            self.task_runner.shutdown(skip_hooks=True)

        # check if end hooks were not called
        self.assertFalse(hasattr(self.plugin, 'test__task_ended'))

        _check_pipe_shutdown(self, self.pipe)
        self.assertFalse(self.task.active)

    def testNoSkipHooks__shutdown(self):
        """ TaskRunner.shutdown: shuts down process, without skipping event
            hooks.
            """
        with self.assertRaises(SystemExit):
            self.task_runner.shutdown(skip_hooks=False)

        # check if end hooks were called
        self.assertTrue(hasattr(self.plugin, 'test__task_ended'))

        _check_pipe_shutdown(self, self.pipe)
        self.assertFalse(self.task.active)


class TestCommandServer(FocusTestCase):
    def setUp(self):
        super(TestCommandServer, self).setUp()
        self.task = MockTask()
        self.task.load()
        self.pipe = MockPipe()
        self.command_server = daemon.CommandServer(self.task, os.getpid(),
                                                   self.pipe)

    def tearDown(self):
        self.plugin = None
        self.task_runner = None
        self.pipe = None
        self.task = None
        super(TestCommandServer, self).tearDown()

    def test___process_commands(self):
        """ CommandServer._process_commands: processes received commands.
            """

        # test existing command received
        self.pipe.send_bytes('SHL\x80ls')  # run `ls` shell command
        self.assertTrue(self.command_server._process_commands())
        self.assertEqual(self.pipe.recv_bytes(), 'OK')  # sent 'OK' response

        # test non-existent command received
        self.pipe.send_bytes('SHL\x80non-exist')
        self.assertTrue(self.command_server._process_commands())
        self.assertEqual(self.pipe.recv_bytes(), 'FAIL')  # send 'FAIL' resp.

        # test TRM sentinel value received
        self.pipe.send_bytes('TRM')
        self.assertFalse(self.command_server._process_commands())
