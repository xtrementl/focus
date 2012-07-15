import os
from datetime import datetime, timedelta

from focus import errors
from focus.task import Task
from focus.plugin import registration
from focus_unittest import FocusTestCase, MockPlugin

_ACTIVE_FILE_DATA = """active_task {
    name "test";
    start_time "2012-04-23 15:18:22.000000";
}
"""

_TASK_FILE_DATA = """task {
    test_opt 12345;
    test_block {
      test_opt name;
      test_opt "name 2";
    }
}
"""


class TestTask(FocusTestCase):
    def _get_pidfile(self):
        return os.path.join(self.task.base_dir, '.focusd.pid')

    def setUp(self):
        super(TestTask, self).setUp()
        self.setup_dir()
        self.task = Task(base_dir=self.test_dir)

        base_dir = self.task._paths['base_dir']
        self.task._paths['task_dir'] = os.path.join(base_dir, 'tasks', 'test')
        os.makedirs(self.task._paths['task_dir'])

        # make task config
        self.task_cfg = os.path.join(self.task.task_dir, 'task.cfg')
        open(self.task_cfg, 'w', 0).write(_TASK_FILE_DATA)

        # register some options from the test task config to a mock plugin.
        for k in ('test_opt', 'test_block_test_opt'):
            registration.register('option', k, MockPlugin, {})

    def tearDown(self):
        self.task = None
        registration._option_hooks.clear()
        registration._registered.clear()
        super(TestTask, self).tearDown()

    def test___reset(self):
        """ Task._reset: correct class attributes are reset.
            """
        self.task._name = 'test'
        self.task._start_time = 'AAAA'
        self.task._owner = 999
        self.task._paths['task_dir'] = 'AAA'
        self.task._paths['task_config'] = 'AAA'
        self.task._loaded = True
        self.task._reset()

        self.assertIsNone(self.task._name)
        self.assertIsNone(self.task._start_time)
        self.assertEqual(self.task._owner, os.getuid())
        self.assertIsNone(self.task._paths['task_dir'])
        self.assertIsNone(self.task._paths['task_config'])
        self.assertIsNotNone(self.task._loaded)
        self.assertIsNotNone(self.task._paths['base_dir'])
        self.assertIsNotNone(self.task._paths['active_file'])

    def test___save_active_file(self):
        """ Task._save_active_file: saves active file properly.
            """
        self.task._name = 'test'
        self.task._start_time = datetime(2012, 04, 23, 15, 18, 22)
        self.task._owner = 1000
        self.task._save_active_file()

        self.assertEqual(open(self.task._paths['active_file'], 'r').read(),
                         _ACTIVE_FILE_DATA)

    def testPidFileExistValid___clean_prior(self):
        """ task._clean_prior: pid file exists and is valid, remove file.
            """
        # write example pid file
        filename = self._get_pidfile()
        open(filename, 'w', 0).write('999999\n')

        self.task._loaded = True
        self.assertTrue(self.task._clean_prior())
        self.assertFalse(os.path.isfile(filename))  # was removed

    def testNoPidFile___clean_prior(self):
        """ task._clean_prior: no pid file exists, do nothing.
            """
        self.task._loaded = True
        self.assertFalse(self.task._clean_prior())

    def testPidFileExistsInvalid___clean_prior(self):
        """ task._clean_prior: invalid pid file exists, do nothing.
            """
        # write invalid pid file
        filename = self._get_pidfile()
        open(filename, 'w', 0).write('a#*)#&@!(b\n')

        self.task._loaded = True
        self.assertTrue(self.task._clean_prior())
        self.assertTrue(os.path.isfile(filename))  # didn't remove

    def test___clean(self):
        """ Task._clean: active file is removed.
            """
        open(self.task._paths['active_file'], 'w', 0).write('')
        self.task._clean()
        self.assertFalse(os.path.isfile(self.task._paths['active_file']))

    def testValidActiveFile__load(self):
        """ Task.load: loads a task if the active file is available.
            """
        open(self.task._paths['active_file'], 'w', 0).write(_ACTIVE_FILE_DATA)
        self.task.load()
        self.assertEqual(self.task._name, 'test')
        dt = datetime(2012, 04, 23, 15, 18, 22)
        self.assertEqual(self.task._start_time, dt)
        self.assertEqual(self.task._owner, os.getuid())

    def testInvalidActiveFile__load(self):
        """ Task.load: will not load a task if the active file is missing or
            invalid.
            """
        self.task.load()
        self.assertIsNone(self.task._name)

        open(self.task._paths['active_file'], 'w', 0).write('INVALID FILE')
        self.task.load()
        self.assertIsNone(self.task._name)

        data = _ACTIVE_FILE_DATA[:len(_ACTIVE_FILE_DATA) / 2]
        open(self.task._paths['active_file'], 'w', 0).write(data)
        self.task.load()
        self.assertIsNone(self.task._name)

        # removes active file if it was invalid
        self.assertFalse(os.path.isfile(self.task._paths['active_file']))

    def testTaskValid__start(self):
        """ Task.start: starts a task if task exists and is valid.
            """
        self.assertTrue(self.task.start('test'))
        self.assertTrue(os.path.isfile(self.task._paths['active_file']))
        self.assertEqual(self.task._name, 'test')

    def testTaskNonExist__start(self):
        """ Task.start: fails if task doesn't exist.
            """
        with self.assertRaises(errors.TaskNotFound):
            self.task.start('non-exist')

    def testTaskActive__start(self):
        """ Task.start: fails if task is loaded.
            """
        self.task._loaded = True
        self.task._name = 'test'
        with self.assertRaises(errors.ActiveTask):
            self.task.start('test')

    def testTaskInvalidTaskConfig__start(self):
        """ Task.start: fails if task config for specified task is invalid.
            """
        data = _TASK_FILE_DATA

        open(self.task_cfg, 'w', 0).write('INVALID FILE')
        with self.assertRaises(errors.InvalidTaskConfig):
            self.task.start('test')

        open(self.task_cfg, 'w', 0).write(data.replace('task {', 'invalid {'))
        with self.assertRaises(errors.InvalidTaskConfig):
            self.task.start('test')

        open(self.task_cfg, 'w', 0).write(data.replace('{', '#'))
        with self.assertRaises(errors.InvalidTaskConfig):
            self.task.start('test')

    def testNoActive__stop(self):
        """ Task.stop: fails if no task active.
            """
        self.task._loaded = False
        with self.assertRaises(errors.NoActiveTask):
            self.task.stop()

    def test__exists(self):
        """ Task.exists: returns correct value for task existence.
            """
        self.assertTrue(self.task.exists('test'))
        self.assertFalse(self.task.exists('non-exist'))

    def test__get_config_path(self):
        """ Task.get_config_path: returns correct task config path.
            """
        self.assertEqual(self.task.get_config_path('test'),
                         os.path.join(self.task.base_dir, 'tasks', 'test',
                                      'task.cfg'))

    def testTaskExists__create(self):
        """ Task.create: fails to create task.
            """
        with self.assertRaises(errors.TaskExists):
            self.task.create('test')

    def testNewNoClone__create(self):
        """ Task.create: creates new task.
            """
        # create default task file
        self.task._default_task_config = self.make_file(_TASK_FILE_DATA)

        self.task.create('new_task')
        task_dir = os.path.join(self.task.base_dir, 'tasks', 'new_task')
        task_cfg = os.path.join(task_dir, 'task.cfg')
        self.assertTrue(os.path.isdir(task_dir))
        self.assertTrue(os.path.isfile(task_cfg))

        # confirm default task file was used as template
        with open(task_cfg, 'r') as file_:
            self.assertEqual(file_.read(), _TASK_FILE_DATA)

    def testNewFromClone__create(self):
        """ Task.create: creates new task from existing task.
            """
        self.task.create('new_task2', 'test')
        task_dir = os.path.join(self.task.base_dir, 'tasks', 'new_task2')
        self.assertTrue(os.path.isdir(task_dir))
        self.assertTrue(os.path.isfile(os.path.join(task_dir, 'task.cfg')))

    def testInvalidName__create(self):
        """ Task.create: fails if invalid name provided.
            """
        with self.assertRaises(ValueError):
            self.task.create(None)
        with self.assertRaises(ValueError):
            self.task.create('-sup')

    def test__rename(self):
        """ Task.rename: reanmes task folder.
            """

        # test non-existent old task path
        with self.assertRaises(errors.TaskNotFound):
            self.task.rename('non-exist', 'other')

        # test existing new task path
        test_path = os.path.join(self.task.base_dir, 'tasks', 'new-test')
        os.makedirs(test_path)
        with self.assertRaises(errors.TaskExists):
            self.task.rename('test', 'new-test')

        # test same names
        with self.assertRaises(ValueError):
            self.task.rename('test', 'test')

        # successful task rename
        self.assertTrue(self.task.rename('test', 'test2'))
        old_dir_path = os.path.join(self.task.base_dir, 'tasks', 'test')
        new_dir_path = os.path.join(self.task.base_dir, 'tasks', 'test2')
        self.assertFalse(os.path.exists(old_dir_path))
        self.assertTrue(os.path.exists(new_dir_path))

    def test__remove(self):
        """ Task.remove: removes task folder.
            """
        self.assertTrue(self.task.remove('test'))
        dir_path = os.path.join(self.task.base_dir, 'tasks', 'test')
        self.assertFalse(os.path.exists(dir_path))
        self.assertFalse(self.task.remove('non-exist'))

    def test__get_list_info(self):
        """ Task.get_list_info: returns valid tasks and info.
            """
        # list all
        info = self.task.get_list_info()
        self.assertEqual(info[0][0], 'test')
        self.assertEqual(list(info[0][1]), [['test_opt', ['12345']]])
        self.assertEqual(list(info[0][2]), [
            ['test_block', [
                ['test_opt', ['name']],
                ['test_opt', ['name 2']]
            ]]
        ])

        # existing match
        info = self.task.get_list_info('test')
        self.assertEqual(info[0][0], 'test')
        self.assertEqual(list(info[0][1]), [['test_opt', ['12345']]])
        self.assertEqual(list(info[0][2]), [
            ['test_block', [
                ['test_opt', ['name']],
                ['test_opt', ['name 2']]
            ]]
        ])

        # non-exist match
        info = self.task.get_list_info('non-exist')
        self.assertEqual(info, [])

    def testActiveTask__stop(self):
        """ Task.stop: removes active file for task.
            """
        self.task._loaded = True
        open(self.task._paths['active_file'], 'w', 0).write('')
        self.task.stop()
        self.assertFalse(os.path.isfile(self.task._paths['active_file']))

    def test__set_total_duration(self):
        """ Task.set_total_duration: Correctly sets total task duration.
            """
        self.task.set_total_duration(15)
        self.assertEqual(self.task._total_duration, 15)

    def test__dunderStr(self):
        """ Task.__str__: returns proper str version.
            """
        self.assertEqual(str(self.task),
            'Task (name=<No Name>, duration=<1m)')
        self.task._name = 'Test'
        self.assertEqual(str(self.task),
            'Task (name=Test, duration=<1m)')

    def test__dunderUnicode(self):
        """ Task.__unicode__: returns proper unicode version.
            """
        self.assertEqual(unicode(self.task),
            u'Task (name=<No Name>, duration=<1m)')
        self.task._name = 'Test'
        self.assertEqual(unicode(self.task),
            u'Task (name=Test, duration=<1m)')

    def testNotLoaded__active(self):
        """ Task.active (property): false when task not loaded.
            """
        self.assertFalse(self.task.active)

    def testNoActiveFile__active(self):
        """ Task.active (property): false if active file not found.
            """
        self.task._loaded = True
        self.assertFalse(self.task.active)  # no active file

    def testLoadedActiveFile__active(self):
        """ Task.active (property): true if active file exists and task loaded.
            """
        self.task._loaded = True
        open(self.task._paths['active_file'], 'w', 0).write('')
        self.assertTrue(self.task.active)

    def testNoName__name(self):
        """ Task.name (property): no name correct value.
            """
        self.assertEqual(self.task.name, u'<No Name>')

    def testHasName__name(self):
        """ Task.name (property): name correct value.
            """
        self.task._name = u'bob'
        self.assertEqual(self.task.name, u'bob')

    def testDefaultOwner__owner(self):
        """ Task.owner (property): default value.
            """
        self.assertEqual(self.task.owner, os.getuid())

    def testHasOwner__owner(self):
        """ Task.owner (property): owner correct value.
            """
        self.task._owner = 1000
        self.assertEqual(self.task.owner, 1000)

    def testTaskNotLoaded__duration(self):
        """ Task.duration (property): task not loaded, returns 0.
            """
        self.task._loaded = False
        self.task._start_time = datetime.now() + timedelta(minutes=-15)
        self.assertEqual(self.task.duration, 0)

    def testTaskLoaded__duration(self):
        """ Task.duration (property): task loaded, returns correct duration.
            """
        self.task._loaded = True
        self.task._start_time = datetime.now() + timedelta(minutes=-15)
        self.assertEqual(self.task.duration, 15)

    def test__elapsed(self):
        """ Task.elapsed (property): returns correct elapsed status.
            """
        self.task._loaded = True

        # not elapsed
        self.task._start_time = datetime.now() + timedelta(minutes=-15)
        self.task._total_duration = 30
        self.assertFalse(self.task.elapsed)

        # elapsed
        self.task._start_time = datetime.now() + timedelta(minutes=-15)
        self.task._total_duration = 15
        self.assertTrue(self.task.elapsed)

        # elapsed, overrun
        self.task._total_duration = 15
        self.task._start_time = datetime.now() + timedelta(minutes=-25)
        self.assertTrue(self.task.elapsed)

    def test__base_dir(self):
        """ Task.base_dir (property): returns correct base_dir.
            """
        self.assertEqual(self.task.base_dir, self.test_dir)

    def test__task_dir(self):
        """ Task.task_dir (property): returns correct task_dir.
            """
        path = os.path.join(self.test_dir, 'tasks', 'test')
        self.assertEqual(self.task.task_dir, path)
