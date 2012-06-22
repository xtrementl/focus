from focus.plugin.base import Plugin
from focus_unittest import FocusTestCase


class TestPlugin(FocusTestCase):
    def setUp(self):
        super(TestPlugin, self).setUp()
        self.plugin = Plugin()

    def tearDown(self):
        self.plugin = None
        super(TestPlugin, self).tearDown()

    def testAllAttributes(self):
        """ Plugin base: all supported attributes are defined.
            """
        keys = ('name', 'version', 'target_version', 'command', 'events',
                'options', 'needs_root', 'task_only')

        for k in keys:
            val = getattr(self.plugin, k, 'TESTVAL')

            if k in ('needs_root', 'task_only'):
                self.assertFalse(val)
            else:
                self.assertIsNone(val)

    def testAllMethods(self):
        """ Plugin base: all supported methods exist.
            """
        keys = ('disable', 'on_taskstart', 'on_taskrun', 'on_taskend',
                'parse_option', 'execute')
        for k in keys:
            method = getattr(self.plugin, k, 'TESTVAL')
            self.assertIsNotNone(method)
            self.assertTrue(callable(method))
