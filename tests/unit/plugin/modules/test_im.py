from focus.plugin.modules import im as plugins
from focus_unittest import (
    FocusTestCase, IS_MACOSX, skipUnless, skipIf
)


class IMStatusCase(FocusTestCase):
    def setUp(self):
        super(IMStatusCase, self).setUp()
        self.plugin = plugins.IMStatus()

    def tearDown(self):
        self.plugin = None
        super(IMStatusCase, self).tearDown()

    def testValidStatusType__parse_option(self):
        """ IMStatus.parse_option: parses status types correctly.
            """
        self.assertEqual(self.plugin.statuses, {})
        for status in self.plugin.VALID_STATUSES:
            for key in ('status', 'end_status', 'timer_status'):
                self.plugin.parse_option(key, 'im',
                                         status, 'msg')

                if key == 'status':
                    key = 'start_' + key
                key = key.split('_', 1)[0]

                self.assertIn(key, self.plugin.statuses)
                self.assertEqual(self.plugin.statuses[key], (status, 'msg'))

    def testValidStatusMsg__parse_option(self):
        """ IMStatus.parse_option: parses status messages correctly.
            """
        self.assertEqual(self.plugin.messages, {})
        for key in ('name1', 'name2', 'name3'):
            value = 'value999'
            self.plugin.parse_option('status_msg', 'im',
                                     key, value)
            self.assertIn(key, self.plugin.messages)
            self.assertEqual(self.plugin.messages[key], value)

    def testInvalidStatusType__parse_option(self):
        """ IMStatus.parse_option: validates status types.
            """
        for key in ('status', 'end_status', 'timer_status'):
            with self.assertRaises(TypeError):
                self.plugin.parse_option(key, 'im',
                                         'away', '2', '3', '4')
            with self.assertRaises(ValueError):
                self.plugin.parse_option(key, 'im',
                                         'invalid-type')
    
    def testInvalidStatusMsg__parse_option(self):
        """ IMStatus.parse_option: validates status messages.
            """
        with self.assertRaises(TypeError):
            self.plugin.parse_option('status_msg', 'im',
                                     'name', 'value', '2', '3')

    @skipUnless(IS_MACOSX, 'for mac osx')
    def testMac___set_status(self):
        """ IMStatus._set_status: installs correct functions for mac osx.
            """
        self.assertEquals(self.plugin.set_status_funcs, (
           plugins._adium_status, plugins._osx_skype_status 
        ))

    @skipIf(IS_MACOSX, 'for linux/nix')
    def testRegular___set_status(self):
        """ IMStatus._set_status: installs correct functions for linux/nix.
            """
        self.assertEquals(self.plugin.set_status_funcs, (
            plugins._pidgin_status, plugins._empathy_status,
            plugins._linux_skype_status
        ))

    def testCallStatusFuncs___set_status(self):
        """ IMStatus._set_status: calls functions within set_status_funcs.
            """

        ret_items = []
        def _check_func(status, message):
            ret_items.append((status, message))
        self.plugin.set_status_funcs = (_check_func, _check_func)

        self.plugin._set_status('away', 'message-here')
        for item in ret_items:
            self.assertEqual(item, ('away', 'message-here'))
