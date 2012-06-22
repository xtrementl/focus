from focus.errors import HelpBanner
from focus.version import __version__
from focus.environment.cli import FocusArgParser, CLI
from focus_unittest import FocusTestCase, MockEnvironment


class TestFocusArgParser(FocusTestCase):
    def setUp(self):
        super(TestFocusArgParser, self).setUp()
        self.parser = FocusArgParser()

    def testMessageDefStatus__exit(self):
        """ FocusArgParser.exit: message, default status.
            """
        message = 'the message'
        with self.assertRaises(HelpBanner) as cm:
            self.parser.exit(message=message)

        exc = cm.exception
        self.assertEqual(exc.code, 0)
        self.assertEqual(exc.description, message)

    def testMessageStatusSet__exit(self):
        """ FocusArgParser.exit: message and status set.
            """
        message = 'the message'
        with self.assertRaises(HelpBanner) as cm:
            self.parser.exit(message=message, status=999)

        exc = cm.exception
        self.assertEqual(exc.code, 999)
        self.assertEqual(exc.description, message)

    def testStripsSubparse__format_help(self):
        """ FocusArgParser.format_help: strips out subparser section.
            """
        sp = self.parser.add_subparsers()
        sp.add_parser('subcmd1')
        sp.add_parser('subcmd2')
        msg = super(FocusArgParser, self.parser).format_help()
        self.assertRegexpMatches(msg, r'\{.+\}')

        msg = self.parser.format_help()
        self.assertNotRegexpMatches(msg, r'\{.+\}')

    def testIgnoresMessage__error(self):
        """ FocusArgParser.error: fails with message from `format_help()`,
            ignores provided message.
            """
        message = 'the message'
        with self.assertRaises(HelpBanner) as cm:
            self.parser.error(message=message)
        self.assertNotRegexpMatches(cm.exception.description, message)

    def test__print_help(self):
        """ FocusArgParser.print_help: fails with message from `format_help()`.
            """
        with self.assertRaises(HelpBanner) as cm:
            self.parser.print_help()
        self.assertEqual(cm.exception.description, self.parser.format_help())


class TestCLI(FocusTestCase):
    def setUp(self):
        super(TestCLI, self).setUp()
        self.cli = CLI()
        self.env = MockEnvironment()

    def tearDown(self):
        self.env = None
        self.cli = None
        super(TestCLI, self).tearDown()

    def testNoArguments__execute(self):
        """ CLI.execute: prints help banner if no arguments passed.
            """
        with self.assertRaises(HelpBanner):
            self.cli.execute(self.env)

    def testHelpArgument__execute(self):
        """ CLI.execute: prints help banner if 'help' argument passed.
            """
        with self.assertRaises(HelpBanner):
            self.env.args = ('help',)
            self.cli.execute(self.env)

    def testVersionArgument__execute(self):
        """ CLI.execute: prints version string if 'version' argument passed.
            """
        self.env.args = ('version',)
        self.cli.execute(self.env)
        self.assertEqual(str(self.env.io.test__write_data),
                         'focus version {0}\n'.format(__version__))

    def testNoColorArgument__execute(self):
        """ CLI.execute: disables colored output if '--no-color' argument
            passed.
            """
        self.assertTrue(self.env.io.colored)
        with self.assertRaises(HelpBanner):
            self.env.args = ('--no-color', 'help')
            self.cli.execute(self.env)
        self.assertFalse(self.env.io.colored)

    def testCommandNoMatchPlugins__execute(self):
        """ CLI.execute: command doesn't match command plugins, raises help
            banner.
            """
        with self.assertRaises(HelpBanner):
            self.env.args = ('no-exist',)
            self.cli.execute(self.env)
