import os

from focus.plugin import registration
from focus.errors import UserPluginImport
from focus.environment import Environment
from focus_unittest import FocusTestCase, MockIOStream, MockTask


class TestEnvironment(FocusTestCase):
    def setUp(self):
        super(TestEnvironment, self).setUp()
        self.setup_dir()
        self.env = Environment(data_dir=self.test_dir, io=MockIOStream(),
                               task=MockTask())

    def tearDown(self):
        self.env = None
        super(TestEnvironment, self).tearDown()

    def testDirectorySetup__load(self):
        """ Environment.load: directory structure is properly established.
            """
        self.env.load()

        paths = [self.env._data_dir]
        paths += [os.path.join(self.env._data_dir, name) for name
                    in self.env.DATA_SUBDIRS]

        for path in paths:
            self.assertTrue(os.path.isdir(path))

    def testPluginsFail__load(self):
        """ Environment.load: fails if error occurs when loading plugins.
            """
        # test user plugin import error
        plugin_dir = os.path.join(self.env._data_dir, 'plugins')
        os.makedirs(plugin_dir)
        filename = os.path.join(plugin_dir, 'errtestplugin.py')
        open(filename, 'w', 0).write('1/0')
        with self.assertRaises(UserPluginImport):
            self.env.load()

        # clean up
        self.clean_paths(filename, filename + 'c')

    def testGoodPlugins__load(self):
        """ Environment.load: successfully loads valid plugins.
            """
        # build test command plugin and load
        plugin_dir = os.path.join(self.env._data_dir, 'plugins')
        os.makedirs(plugin_dir)
        filename = os.path.join(plugin_dir, 'testplugin.py')
        with open(filename, 'w', 0) as f:
            f.write('from focus.plugin import Plugin\n')
            f.write('class MyTestPlugin(Plugin):\n')
            f.write('  name = "MyTestPlugin"\n')
            f.write('  target_version = ">=0.1.0"\n')
            f.write('  version = "1.0"\n')
            f.write('  command = "oh_hai"\n')
            f.write('  def execute(self, env): env.io.write("You rang.")\n')
            f.write('  def help(self, env): return u"focus oh_hai"\n')
        self.env.load()

        # confirm plugin registration in a couple ways..
        # 1) scan registered list
        # 2) get command hook version
        # 3) execute methods and compare
        plugin = None
        for p in registration.get_registered(command_hooks=True):
            if p.name == 'MyTestPlugin':
                plugin = p
                break

        success = False
        if plugin:
            test_plugin = registration.get_command_hook('oh_hai')
            if test_plugin == plugin:
                # test execute()
                plugin.execute(self.env)
                self.assertEqual(self.env.io.test__write_data, 'You rang.\n')

                # test help()
                data = plugin.help(self.env)
                self.assertEqual(data, u'focus oh_hai')
                success = True

        self.assertTrue(success)

        # clean up
        self.clean_paths(filename, filename + 'c')

    def testTaskSetup__load(self):
        """ Environment.load: task is setup and loaded.
            """
        self.env.load()
        self.assertIsNotNone(self.env._task)
        self.assertTrue(self.env._task._loaded)

    def test__loaded(self):
        """ Environment.loaded (property): correct value for loaded.
            """
        self.assertEqual(self.env._loaded, self.env.loaded)

    def test__args(self):
        """ Environment.args (property): correct value for args.
            """
        self.assertEqual(self.env._args, self.env.args)

    def test__io(self):
        """ Environment.io (property): correct value for io.
            """
        self.assertEqual(self.env._io, self.env.io)

    def test__data_dir(self):
        """ Environment.data_dir (property): correct value for data_dir.
            """
        self.assertEqual(self.env._data_dir, self.env.data_dir)

    def test__task(self):
        """ Environment.task (property): correct value for task.
            """
        self.assertEqual(self.env._task, self.env.task)
