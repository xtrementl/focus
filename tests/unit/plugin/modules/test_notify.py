from focus.plugin.modules import notify as plugins
from focus_unittest import (
    MockTask, FocusTestCase, IS_MACOSX, skipUnless, skipIf
)


class NotifyCase(FocusTestCase):
    def setUp(self):
        super(NotifyCase, self).setUp()
        self.plugin = plugins.Notify()

    def tearDown(self):
        self.plugin = None
        super(NotifyCase, self).tearDown()

    def testValidMessageType__parse_option(self):
        """ Notify.parse_option: parses message types correctly.
            """
        self.assertEqual(self.plugin.messages, {})
        for key in ('show', 'end_show', 'timer_show'):
            self.plugin.parse_option(key, 'show', 'msg')

            if key == 'show':
                key = 'start_' + key
            key = key.split('_', 1)[0]

            self.assertIn(key, self.plugin.messages)
            self.assertEqual(self.plugin.messages[key], 'msg')

    def testInvalidMessageType__parse_option(self):
        """ Notify.parse_option: validates message types.
            """
        for key in ('show', 'end_show', 'timer_show'):
            with self.assertRaises(TypeError):
                self.plugin.parse_option(key, 'notify',
                                         'test-message', '2', '3', '4')
    
    @skipUnless(IS_MACOSX, 'for mac osx')
    def testMac___notify(self):
        """ Notify._notify: installs correct functions for mac osx.
            """
        self.assertIn(self.plugin.notify_func, (
           plugins._terminal_notifier,
           plugins._growlnotify,
           plugins._osx_popup
        ))

    @skipIf(IS_MACOSX, 'for linux/nix')
    def testRegular___notify(self):
        """ Notify._notify: installs correct functions for linux/nix.
            """
        self.assertEquals(self.plugin.notify_func, plugins._dbus_notify)

    def testCallNotifyFunc___notify(self):
        """ Notify._notify: calls function defined by notify_func.
            """

        test_task = MockTask()
        test_task.start('Test-Task')

        ret_items = []
        def _check_func(task, message):
            ret_items.append((task, message))
        self.plugin.notify_func = _check_func

        self.plugin._notify(test_task, 'message-here')
        for item in ret_items:
            self.assertEqual(item, ('Focus ({0})'.format(test_task.name),
                                    'message-here'))
