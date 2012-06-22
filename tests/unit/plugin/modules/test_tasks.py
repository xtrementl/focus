import os
import types

from focus import errors
from focus.plugin import registration
from focus.plugin.modules import tasks as plugins
from focus_unittest import FocusTestCase, MockEnvironment, MockPlugin


_TASK_FILE_DATA = """task {
    test_opt 12345;
    test_block {
      test_opt name;
      test_opt "name 2";
    }
}
"""


class TestTaskStart(FocusTestCase):
    class ParsedArgs(object):
        pass

    def setUp(self):
        super(TestTaskStart, self).setUp()
        self.env = MockEnvironment()
        self.plugin = plugins.TaskStart()

    def tearDown(self):
        self.plugin = None
        self.env = None
        super(TestTaskStart, self).tearDown()

    def test__execute(self):
        """ TaskStart.execute: calls task.start() and prints task loaded.
            """
        args = self.ParsedArgs()
        args.task_name = 'test_task'
        self.plugin.execute(self.env, args)

        self.assertEqual(self.env.io.test__success_data, 'Task Loaded.\n')
        self.assertTrue(self.env.task._loaded)


class TestTaskStop(FocusTestCase):
    class ParsedArgs(object):
        pass

    def setUp(self):
        super(TestTaskStop, self).setUp()
        self.env = MockEnvironment()
        self.plugin = plugins.TaskStop()

    def tearDown(self):
        self.plugin = None
        self.env = None
        super(TestTaskStop, self).tearDown()

    def test__execute(self):
        """ TaskStop.execute: calls task.stop().
            """
        self.env.task._loaded = True
        self.plugin.execute(self.env, self.ParsedArgs())
        self.assertFalse(self.env.task._loaded)


class TestTaskCreate(FocusTestCase):
    class ParsedArgs(object):
        skip_edit = True
        clone_task = None

    def setUp(self):
        super(TestTaskCreate, self).setUp()
        self.env = MockEnvironment()
        self.plugin = plugins.TaskCreate()

    def tearDown(self):
        self.plugin = None
        self.env = None
        super(TestTaskCreate, self).tearDown()

    def test__execute(self):
        """ TaskCreate.execute: create specified task.
            """
        # create
        args = self.ParsedArgs()
        args.task_name = 'test1'
        self.plugin.execute(self.env, args)
        self.assertEqual(self.env.task.test__created[0][0], 'test1')

        # check exist fail
        with self.assertRaises(errors.TaskExists):
            self.plugin.execute(self.env, args)

        # clone from
        args.task_name = 'test2'
        args.clone_task = 'blah'
        self.plugin.execute(self.env, args)
        self.assertEqual(self.env.task.test__created[1][0], 'test2')
        self.assertEqual(self.env.task.test__created[1][1], 'blah')


class TestTaskEdit(FocusTestCase):
    class ParsedArgs(object):
        task_name = None

    def setUp(self):
        super(TestTaskEdit, self).setUp()
        self.plugin = plugins.TaskEdit()
        self.env = MockEnvironment()

        # patch editor environment variable to /bin/cat with suppressed output
        if 'EDITOR' in os.environ:
            self.old_editor = os.environ['EDITOR']
        os.environ['EDITOR'] = 'cat >/dev/null '

        # setup test dir and task
        self.setup_dir()
        self.env.task._base_dir = self.test_dir
        self.env.task._task_dir = os.path.join(self.test_dir, 'tasks', 'test')
        os.makedirs(self.env.task._task_dir)

        # make task config
        self.task_cfg = os.path.join(self.env.task._task_dir, 'task.cfg')
        open(self.task_cfg, 'w', 0).write(_TASK_FILE_DATA)

        # register some options from the test task config to a mock plugin.
        for k in ('test_opt', 'test_block_test_opt'):
            registration.register('option', k, MockPlugin, {})

    def tearDown(self):
        if hasattr(self, 'old_editor'):
            os.environ['EDITOR'] = self.old_editor
        else:
            del os.environ['EDITOR']

        self.plugin = None
        self.env = None

        registration._option_hooks.clear()
        registration._registered.clear()
        super(TestTaskEdit, self).tearDown()

    def testExist__execute(self):
        """ TaskEdit.execute: edits existing task.
            """
        args = self.ParsedArgs()
        args.task_name = 'test'

        self.plugin.execute(self.env, args)
        self.assertIsNone(self.env.io.test__error_data)

    def testExistActiveTask__execute(self):
        """ TaskEdit.execute: fails for editing active task.
            """
        self.env.task.name = 'test'
        self.env.task.load()
        args = self.ParsedArgs()
        args.task_name = 'test'

        with self.assertRaises(errors.ActiveTask):
            self.plugin.execute(self.env, args)

    def testExistFailEdit__execute(self):
        """ TaskEdit.execute: fails to edit existing task.
            """
        os.environ['EDITOR'] = 'false'
        args = self.ParsedArgs()
        args.task_name = 'test'

        with self.assertRaises(errors.FocusError) as cm:
            self.plugin.execute(self.env, args)

        output = cm.exception.description
        self.assertRegexpMatches(output, r'Could not open task config')

    def testNoExistTask__execute(self):
        """ TaskEdit.execute: fails for non-existent task.
            """
        args = self.ParsedArgs()
        args.task_name = 'non-exist'

        with self.assertRaises(errors.TaskNotFound):
            self.plugin.execute(self.env, args)


class TestTaskRename(FocusTestCase):
    class ParsedArgs(object):
        old_task_name = None
        new_task_name = None

    def setUp(self):
        super(TestTaskRename, self).setUp()
        self.plugin = plugins.TaskRename()
        self.env = MockEnvironment()

        # setup test dir
        self.setup_dir()
        self.env.task._base_dir = self.test_dir
        self.env.task._task_dir = os.path.join(self.test_dir, 'tasks', 'test')
        os.makedirs(self.env.task._task_dir)

    def tearDown(self):
        self.env = None
        self.plugin = None
        super(TestTaskRename, self).tearDown()

    def test__execute(self):
        """ TaskRename.execute: renames specified task.
            """
        # pretend exists
        self.env.task.test__renamed = dict(test=True, test2=True)

        args = self.ParsedArgs()

        # test new task already exists
        args.old_task_name = 'test'
        args.new_task_name = 'test2'
        with self.assertRaises(errors.TaskExists):
            self.plugin.execute(self.env, args)

        # successful rename
        args.new_task_name = 'test1'
        self.plugin.execute(self.env, args)
        self.assertIn('test1', self.env.task.test__renamed)
        self.assertNotIn('test', self.env.task.test__renamed)

        # test old task not exists
        with self.assertRaises(errors.TaskNotFound):
            self.plugin.execute(self.env, args)

        # test task rename itself
        args.old_task_name = 'test1'
        with self.assertRaises(errors.FocusError) as cm:
            self.plugin.execute(self.env, args)

        output = cm.exception.description
        self.assertEqual(output, u'Could not rename task to itself')


class TestTaskRemove(FocusTestCase):
    class ParsedArgs(object):
        task_name = None
        force = False

    def setUp(self):
        super(TestTaskRemove, self).setUp()
        self.plugin = plugins.TaskRemove()
        self.env = MockEnvironment()

        # setup test dir
        self.setup_dir()
        self.env.task._base_dir = self.test_dir
        self.env.task._task_dir = os.path.join(self.test_dir, 'tasks', 'test')
        os.makedirs(self.env.task._task_dir)

    def tearDown(self):
        self.env = None
        self.plugin = None
        super(TestTaskRemove, self).tearDown()

    def testExists__execute(self):
        """ TaskRemove.execute: removes existing task.
            """
        args = self.ParsedArgs()
        args.task_name = 'test'
        args.force = True

        self.plugin.execute(self.env, args)
        self.assertFalse(self.env.task.exists('test'))

    def testNoExist__execute(self):
        """ TaskRemove.execute: fails for non-existent task.
            """
        args = self.ParsedArgs()
        args.task_name = 'non-exist'

        with self.assertRaises(errors.TaskNotFound):
            self.plugin.execute(self.env, args)

    def testExistActiveTask__execute(self):
        """ TaskRemove.execute: fails for active task.
            """
        self.env.task.name = 'test'
        self.env.task.load()
        args = self.ParsedArgs()
        args.task_name = 'test'

        with self.assertRaises(errors.ActiveTask):
            self.plugin.execute(self.env, args)


class TestTaskList(FocusTestCase):
    class ParsedArgs(object):
        verbose = False

    def setUp(self):
        super(TestTaskList, self).setUp()
        self.env = MockEnvironment()
        self.plugin = plugins.TaskList()

    def tearDown(self):
        self.plugin = None
        self.env = None
        super(TestTaskList, self).tearDown()

    def testVerbose__execute(self):
        """ TaskList.execute: check verbose prints task names.
            """
        args = self.ParsedArgs()
        args.verbose = True
        self.plugin.execute(self.env, args)

        output = self.env.io.test__write_data
        for name in ('test1', 'test2'):
            self.assertRegexpMatches(output, name)

    def testNonVerbose__execute(self):
        """ TaskList.execute: check non-verbose prints task names.
            """
        args = self.ParsedArgs()
        args.verbose = False
        self.plugin.execute(self.env, args)

        output = self.env.io.test__write_data
        self.assertEqual(output, 'test1\ntest2\n')

    def testNoTasks__execute(self):
        """ TaskList.execute: prints error if no tasks found.
            """
        self.env.task.get_list_info = types.MethodType(lambda name: [],
                                                       self.env.task)
        self.plugin.execute(self.env, self.ParsedArgs())
        self.assertEqual(self.env.io.test__write_data, 'No tasks found.\n')


class TestTaskView(FocusTestCase):
    class ParsedArgs(object):
        task_name = None

    def setUp(self):
        super(TestTaskView, self).setUp()
        self.env = MockEnvironment()
        self.plugin = plugins.TaskView()

    def tearDown(self):
        self.plugin = None
        self.env = None
        super(TestTaskView, self).tearDown()

    def testTaskName__execute(self):
        """ TaskView.execute: checks output for task name.
            """
        args = self.ParsedArgs()
        args.task_name = 'test1'
        self.plugin.execute(self.env, args)

        output = self.env.io.test__write_data
        self.assertRegexpMatches(output, r'test1')

    def testNotActive__execute(self):
        """ TaskList.execute: prints error if not active, no task provided.
            """
        args = self.ParsedArgs()
        args.task_name = None
        self.assertFalse(self.env.task.active)
        with self.assertRaises(errors.NoActiveTask):
            self.plugin.execute(self.env, args)

    def testActive__execute(self):
        """ TaskList.execute: prints active task if no task provided.
            """
        args = self.ParsedArgs()
        args.task_name = None
        self.env.task.load()
        self.env.task.name = 'test1'
        self.assertTrue(self.env.task.active)
        self.plugin.execute(self.env, args)

        output = self.env.io.test__write_data
        self.assertRegexpMatches(output, r'test1')
