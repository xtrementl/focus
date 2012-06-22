import os
import types

from focus.plugin import registration
from focus_unittest import FocusTestCase, MockTask, MockPlugin


class TestPluginRegistration(FocusTestCase):
    class MockParser(object):
        options = []
        blocks = []

    def setUp(self):
        super(TestPluginRegistration, self).setUp()
        registration._event_hooks = {}
        registration._option_hooks.clear()
        registration._command_hooks.clear()
        registration._registered.clear()

    def tearDown(self):
        registration._event_hooks = {}
        registration._option_hooks.clear()
        registration._command_hooks.clear()
        registration._registered.clear()
        super(TestPluginRegistration, self).tearDown()

    def testCommandHook__register(self):
        """ registration.register: registers a command plugin.
            """
        command = MockPlugin.command
        registration.register('command', command, MockPlugin)
        self.assertIsInstance(registration._command_hooks.get(command),
                              MockPlugin)

    def testEventHook__register(self):
        """ registration.register: registers a task event plugin.
            """
        registration.register('event', 'task_start', MockPlugin)
        event_chain = registration._event_hooks.get('task_start')

        for _, fn_ in event_chain:
            if isinstance(fn_(), MockPlugin):
                found = True
                break
        else:
            found = False
        self.assertTrue(found)

    def testOptionHook__register(self):
        """ registration.register: registers a plugin using option hooks.
            """
        registration.register('option', 'apps_sup', MockPlugin, {})
        item = registration._option_hooks.get('apps_sup')
        self.assertIsNotNone(item)

        plugin, props = item
        self.assertIsInstance(plugin, MockPlugin)

    def test__register_all(self):
        """ registration.register_all: handles registration for all hook types
            defined for the provided plugin.
            """
        # register all for plugin
        registration.register_all(MockPlugin)
        command = MockPlugin.command
        self.assertIn(command, [x[0] for x in registration._command_hooks])
        self.assertIn('apps_sup', [x[0] for x in registration._option_hooks])

        found_count = 0
        for k, v in registration._event_hooks.iteritems():
            if k in ('task_start', 'task_run', 'task_end'):
                name, get_plugin = v[0]
                plugin_obj = get_plugin()

                self.assertEqual(name, MockPlugin.name)
                self.assertIsInstance(plugin_obj, MockPlugin)
                found_count += 1
        self.assertEqual(found_count, 3)

    def test__setup_sudo_access(self):
        """ registration.setup_sudo_access: installs a sudo-based `run_root`
            method onto the provided plugin.
            """
        plugin = MockPlugin()
        registration.setup_sudo_access(plugin)

        # check if method was injected
        method = getattr(plugin, 'run_root', None)
        self.assertIsNotNone(method)
        self.assertTrue(callable(method))

        # at this point, we could run the method to test it, but let's assume
        # it works; otherwise, we'll have to enter sudo password every time we
        # need to run tests---that's annoying to automate.

    def testFilterAll__get_registered(self):
        """ registration.get_registered: returns all registered plugins.
            """
        registration._registered.register(MockPlugin.name, MockPlugin,
                                          {'command': True})
        self.assertIn(MockPlugin.name,
                      [x.name for x in registration.get_registered()])

    def testFilterCommandHook__get_registered(self):
        """ registration.get_registered: returns all registered command
            plugins.
            """
        class MockPlugin2(MockPlugin):
            name = 'hai 2'

        # register a command and event plugin
        registration._registered.register(MockPlugin.name, MockPlugin,
                                          {'event': True})
        registration._registered.register(MockPlugin2.name, MockPlugin2,
                                          {'command': True})

        # get list of registered names for command plugins
        plugin_names = [x.name for x in
                            registration.get_registered(command_hooks=True)]

        # make sure MockPlugin2 is the only command plugin
        self.assertNotIn(MockPlugin.name, plugin_names)
        self.assertIn(MockPlugin2.name, plugin_names)

    def testFilterEventHook__get_registered(self):
        """ registration.get_registered: returns all registered task event
            plugins.
            """
        class MockPlugin2(MockPlugin):
            name = 'hai 2'

        # register a command and event plugin
        registration._registered.register(MockPlugin.name, MockPlugin,
                                          {'event': True})
        registration._registered.register(MockPlugin2.name, MockPlugin2,
                                          {'command': True})

        # get list of registered names for event plugins
        plugin_names = [x.name for x in
                            registration.get_registered(event_hooks=True)]

        # make sure MockPlugin is the only event plugin
        self.assertIn(MockPlugin.name, plugin_names)
        self.assertNotIn(MockPlugin2.name, plugin_names)

    def testFilterActiveTask__get_registered(self):
        """ registration.get_registered: returns all registered
            plugins that are available when a task is active.
            """
        class MockPlugin2(MockPlugin):
            name = 'hai 2'
            options = None

        class MockPlugin3(MockPlugin):
            name = 'hai 3'
            options = None
            task_only = True

        # register a couple test plugins
        registration._registered.register(MockPlugin.name, MockPlugin,
                                          {'event': True})
        registration._registered.register(MockPlugin2.name, MockPlugin2,
                                          {'command': True})
        registration._registered.register(MockPlugin3.name, MockPlugin3,
                                          {'command': True})

        # get list of registered names for active task plugins
        plugin_names = [x.name for x in
                            registration.get_registered(task_active=True)]

        self.assertIn(MockPlugin.name, plugin_names)
        self.assertIn(MockPlugin2.name, plugin_names)
        self.assertIn(MockPlugin3.name, plugin_names)

    def testFilterNoActiveTask__get_registered(self):
        """ registration.get_registered: returns all registered
            plugins that can be seen when a task is not active.
            """
        class MockPlugin2(MockPlugin):
            name = 'hai 2'
            options = None

        class MockPlugin3(MockPlugin):
            name = 'hai 3'
            options = None
            task_only = True

        # register a couple test plugins
        registration._registered.register(MockPlugin.name, MockPlugin,
                                          {'event': True})
        registration._registered.register(MockPlugin2.name, MockPlugin2,
                                          {'command': True})
        registration._registered.register(MockPlugin3.name, MockPlugin3,
                                          {'command': True})

        # get list of registered names for active task plugins
        plugin_names = [x.name for x in
                            registration.get_registered(task_active=False)]

        # check that only the non-option, task_only=False plugin is returned
        self.assertIn(MockPlugin2.name, plugin_names)
        self.assertNotIn(MockPlugin.name, plugin_names)
        self.assertNotIn(MockPlugin3.name, plugin_names)

    def test__get_command_hook(self):
        """ registration.get_command_hook: returns the registered command
            plugin for the provided key.
            """
        registration._command_hooks.register(MockPlugin.command, MockPlugin)
        command = MockPlugin.command
        self.assertIsInstance(registration.get_command_hook(command),
                              MockPlugin)

    def test__run_event_hooks(self):
        """ registration.run_event_hooks: runs the task event methods for
            registered event plugins.
            """
        plugin = MockPlugin()

        # fake event registration for plugin
        for event in ('task_start', 'task_run', 'task_end'):
            registration._event_hooks[event] = [
                (plugin.name, lambda: plugin)
            ]

            # run event hooks for plugin, check if it works
            registration.run_event_hooks(event, MockTask())

            if event == 'task_start':
                self.assertTrue(hasattr(plugin, 'test__task_started'))

            elif event == 'task_run':
                self.assertTrue(hasattr(plugin, 'test__task_ran'))
                self.assertEqual(plugin.test__task_ran, 1)

            elif event == 'task_end':
                self.assertTrue(hasattr(plugin, 'test__task_ended'))

    def testNoDisableMissing__run_option_hooks(self):
        """ registration.run_option_hooks: runs the parsing methods for
            registered plugins using option hooks; not disabled if missing
            options in the parser.
            """
        parser = self.MockParser()
        parser.blocks = (
                            ('apps', (
                                ('sup', ('val1', 'val2')),
                            )),
                        )

        # fake option registration for plugin
        plugin = MockPlugin()
        registration._registered.register(plugin.name, lambda: plugin,
                                          {'option': True})
        registration._option_hooks.register('apps_sup', lambda: plugin, {})

        # run option hooks for plugin, check if it works
        registration.run_option_hooks(parser, disable_missing=False)
        self.assertTrue(hasattr(plugin, 'test__option'))
        self.assertEqual(plugin.test__option,
                         [('sup', 'apps', ('val1', 'val2'))])

        item = registration._registered.get(plugin.name)
        self.assertIsNotNone(item)
        plugin, props = item
        self.assertFalse(props.get('disabled', False))

        # run option hooks again for plugin using empty parser, confirm test
        # plugin has not been disabled
        registration.run_option_hooks(self.MockParser(),
                                      disable_missing=False)

        self.assertFalse(props.get('disabled'))

    def testDisableMissing__run_option_hooks(self):
        """ registration.run_option_hooks: runs the parsing methods for
            registered plugins using option hooks; disables if missing options
            in the parser.
            """
        # fake option registration for plugin
        registration._registered.register(MockPlugin.name, MockPlugin,
                                          {'option': True})
        registration._option_hooks.register('apps_sup', MockPlugin, {})

        item = registration._registered.get(MockPlugin.name)
        self.assertIsNotNone(item)
        plugin, props = item
        self.assertFalse(props.get('disabled', False))

        # run option hooks for plugin, confirm test plugin has been
        # disabled, since parser didn't have the options that
        # plugin was registered for
        registration.run_option_hooks(self.MockParser(),
                                      disable_missing=True)

        self.assertTrue(props.get('disabled', False))
