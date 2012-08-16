import os
import datetime

try:
    import simplejson as json
except ImportError:
    import json

from focus.plugin.modules import stats as plugins
from focus_unittest import FocusTestCase, MockEnvironment

class TestStats(FocusTestCase):
    class ParsedArgs(object):
        start = None

    def setUp(self):
        super(TestStats, self).setUp()
        self.setup_dir()

        self.env = MockEnvironment(data_dir=self.test_dir)
        self.plugin = plugins.Stats()

    def tearDown(self):
        self.plugin = None
        self.env = None
        super(TestStats, self).tearDown()

    def _get_file(self, date):
        stats_dir = os.path.join(self.test_dir, '.stats')
        if not os.path.exists(stats_dir):
            os.mkdir(stats_dir)

        return os.path.join(stats_dir,
                            '{0}.json'.format(date.strftime('%Y%m%d')))

    def testToday__execute(self):
        """ TestStats.execute: prints stats for today.
            """
        args = self.ParsedArgs()
        filename = self._get_file(datetime.date.today())
        open(filename, 'w').write(json.dumps({"test": 22}))

        args.start = 'today'
        self.plugin.execute(self.env, args)
        output = self.env.io.test__write_data
        self.assertRegexpMatches(output, r'0:22 \(100%\) - test')

        del self.env.io.test__write_data
        args.start = 't'
        self.plugin.execute(self.env, args)
        self.assertEqual(output, self.env.io.test__write_data)

    def testYesterday__execute(self):
        """ TestStats.execute: prints stats for yesterday.
            """
        args = self.ParsedArgs()
        filename = self._get_file(datetime.date.today() -
                                  datetime.timedelta(days=1))
        open(filename, 'w').write(json.dumps({"test": 22}))

        args.start = 'yesterday'
        self.plugin.execute(self.env, args)
        output = self.env.io.test__write_data
        self.assertRegexpMatches(output, r'0:22 \(100%\) - test')

        del self.env.io.test__write_data
        args.start = 'y'
        self.plugin.execute(self.env, args)
        self.assertEqual(output, self.env.io.test__write_data)

    def testDays__execute(self):
        """ TestStats.execute: prints stats for days.
            """
        args = self.ParsedArgs()
        filename = self._get_file(datetime.date.today() -
                                  datetime.timedelta(days=3))
        open(filename, 'w').write(json.dumps({"test": 22}))

        args.start = '3d'
        self.plugin.execute(self.env, args)
        output = self.env.io.test__write_data
        self.assertRegexpMatches(output, r'0:22 \(100%\) - test')

        keys = ('3day', '3days', '3 day', '3days', '3 day ago', '3 days ago')
        for key in keys:
            del self.env.io.test__write_data
            args.start = key
            self.plugin.execute(self.env, args)
            self.assertEqual(output, self.env.io.test__write_data)

    def testWeeks__execute(self):
        """ TestStats.execute: prints stats for weeks.
            """
        args = self.ParsedArgs()
        filename = self._get_file(datetime.date.today() -
                                  datetime.timedelta(days=7))
        open(filename, 'w').write(json.dumps({"test": 22}))

        args.start = '1w'
        self.plugin.execute(self.env, args)
        output = self.env.io.test__write_data
        self.assertRegexpMatches(output, r'0:22 \(100%\) - test')

        keys = ('1wk', '1 week', '1 weeks', '1 week ago', '1 weeks ago')
        for key in keys:
            del self.env.io.test__write_data
            args.start = key
            self.plugin.execute(self.env, args)
            self.assertEqual(output, self.env.io.test__write_data)
