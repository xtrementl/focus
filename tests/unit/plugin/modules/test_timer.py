from focus.errors import HelpBanner
from focus.plugin.modules import timer as plugins
from focus_unittest import FocusTestCase, MockEnvironment


class TestTimer(FocusTestCase):
    class ParsedArgs(object):
        short = False

    def setUp(self):
        super(TestTimer, self).setUp()
        self.plugin = plugins.Timer()
        self.env = MockEnvironment()

    def tearDown(self):
        self.env = None
        self.plugin = None
        super(TestTimer, self).tearDown()

    def test17Left__execute(self):
        """ Timer.execute: 17 mins left.
            """
        self.plugin.total_duration = 30
        self.env.task.duration = 13
        self.plugin.execute(self.env, self.ParsedArgs())
        self.assertEqual(self.env.io.test__write_data, 'Time Left: 17m\n')

    def test17LeftFlags__execute(self):
        """ Timer.execute: 17 mins left. testing short flags.
            """
        args = self.ParsedArgs()
        args.short = True

        self.plugin.total_duration = 30
        self.env.task.duration = 13
        self.plugin.execute(self.env, args)
        self.assertEqual(self.env.io.test__write_data, '17\n')

    def test0Left__execute(self):
        """ Timer.execute: 0 mins left.
            """
        self.plugin.total_duration = 30
        self.env.task.duration = 30
        self.plugin.execute(self.env, self.ParsedArgs())
        self.assertEqual(self.env.io.test__write_data, 'Time Left: 0m\n')

    def test0LeftFlags__execute(self):
        """ Timer.execute: 0 mins left. testing short flags.
            """
        args = self.ParsedArgs()
        args.short = True

        self.plugin.total_duration = 30
        self.env.task.duration = 30
        self.plugin.execute(self.env, args)
        self.assertEqual(self.env.io.test__write_data, '0\n')

    def test0LeftExceed__execute(self):
        """ Timer. execute: 0 mins left, duration > total_duration
            condition.
            """
        self.plugin.total_duration = 30
        self.env.task.duration = 99
        self.plugin.execute(self.env, self.ParsedArgs())
        self.assertEqual(self.env.io.test__write_data, 'Time Left: 0m\n')

    def test0LeftExceedFlags__execute(self):
        """ Timer.execute: 0 mins left, duration > total_duration
            condition. testing short flags.
            """
        args = self.ParsedArgs()
        args.short = True

        self.plugin.total_duration = 30
        self.env.task.duration = 99
        self.plugin.execute(self.env, args)
        self.assertEqual(self.env.io.test__write_data, '0\n')

    def testDuration__parse_option(self):
        """ Timer.parse_option: 30 mins for value of duration option.
            """
        self.plugin.parse_option('duration', None, '30')
        self.assertEqual(self.plugin.total_duration, 30)

    def testZeroDuration__parse_option(self):
        """ Timer.parse_option: zero value for duration option.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('duration', None, '0')

    def testNegDuration__parse_option(self):
        """ Timer.parse_option: negative value for duration option.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('duration', None, '-50')

    def testInvFormatDuration__parse_option(self):
        """ Timer.parse_option: invalid formats for duration option.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('duration', None, 'ABC123')
        with self.assertRaises(ValueError):
            self.plugin.parse_option('duration', None, '22.50')

    def testNonExist_PlayEndAction__parse_option(self):
        """ Timer.parse_option: invalid file provided for
            end_actions.play option.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('play', 'timer_actions', 'non-exist-file')

    def testTimerNotElapsedStart__on_taskrun(self):
        """ Timer.on_taskrun: task just started; timer hasn't elapsed.
            """
        self.plugin.total_duration = 30
        self.env.task.duration = 0
        self.env.task._loaded = True
        self.plugin.on_taskrun(self.env.task)
        self.assertFalse(self.plugin.elapsed)
        self.assertTrue(self.env.task._loaded)

    def testTimerNotElapsedMid__on_taskrun(self):
        """ Timer.on_taskrun: mid-way through task duration; timer hasn't
            elapsed.
            """
        self.plugin.total_duration = 30
        self.env.task.duration = 15
        self.env.task._loaded = True
        self.plugin.on_taskrun(self.env.task)
        self.assertFalse(self.plugin.elapsed)
        self.assertTrue(self.env.task._loaded)

    def testTimerElapsed__on_taskrun(self):
        """ Timer.on_taskrun: task duration reached timer setting; timer
            has elapsed.
            """
        self.plugin.total_duration = 30
        self.env.task.duration = 30
        self.env.task._loaded = True
        self.plugin.on_taskrun(self.env.task)
        self.assertTrue(self.plugin.elapsed)
        self.assertFalse(self.env.task._loaded)

    def testTimerElapsed__on_taskend(self):
        """ Timer.on_taskend: task has ended, end actions run.
            """
        self.env.task._loaded = True
        self.plugin.elapsed = True
        self.plugin.on_taskend(self.env.task)
