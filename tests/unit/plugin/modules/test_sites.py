import os

from focus.plugin.modules import sites as plugins
from focus_unittest import FocusTestCase, MockTask


_HOST_FILE_DATA = """#<ip-address>	<hostname.domain.org>	<hostname>
127.0.0.1	localhost.localdomain	localhost
::1		localhost.localdomain	localhost
"""

_BLKD_HOST_FILE_DATA = """#<ip-address>	<hostname.domain.org>	<hostname>
127.0.0.1	localhost.localdomain	localhost
::1		localhost.localdomain	localhost
127.0.0.1	google.com	# FOCUS
127.0.0.1	m.google.com	# FOCUS
127.0.0.1	m.twitter.com	# FOCUS
127.0.0.1	mobile.google.com	# FOCUS
127.0.0.1	mobile.twitter.com	# FOCUS
127.0.0.1	twitter.com	# FOCUS
127.0.0.1	www.google.com	# FOCUS
127.0.0.1	www.twitter.com	# FOCUS
"""


class TestSiteBlock(FocusTestCase):
    def setUp(self):
        super(TestSiteBlock, self).setUp()
        self.setup_dir()

        self.task = MockTask(base_dir=self.test_dir, make_task_dir=True)
        self.plugin = plugins.SiteBlock()

        self.mock_run_root(self.plugin)
        self.plugin.hosts_file = os.path.join(self.task.task_dir,
                                              'focus_test_hosts')
        open(self.plugin.hosts_file, 'w').write(_HOST_FILE_DATA)
        self.backup_hosts_file = os.path.join(self.task.task_dir,
                                              '.hosts.bak')

    def tearDown(self):
        self.clean_paths(self.plugin.hosts_file, self.backup_hosts_file)

        self.plugin = None
        self.task = None

        super(TestSiteBlock, self).tearDown()

    def testOptionSingleValue__parse_option(self):
        """ SiteBlock.parse_option: option value includes additional
            subdomains for value provided.
            """
        self.plugin.parse_option('block', 'sites', 'google.com')
        self.assertEqual(self.plugin.domains,
            set(['google.com', 'm.google.com',
                 'www.google.com', 'mobile.google.com']))

    def testDedupeOptionValue__parse_option(self):
        """ SiteBlock.parse_option: duplicate values for options should
            be removed.
            """
        self.plugin.parse_option('block', 'sites', 'google.com')
        self.plugin.parse_option('block', 'sites', 'google.com')
        self.assertEqual(self.plugin.domains,
            set(['google.com', 'm.google.com',
                 'www.google.com', 'mobile.google.com']))

    def testMultiValueOption__parse_option(self):
        """ SiteBlock.parse_option: options support multiple values.
            """
        self.plugin.parse_option('block', 'sites', 'www.reddit.com',
                                 'google.com', 'twitter.com')
        self.assertEqual(self.plugin.domains,
            set(['reddit.com', 'm.reddit.com', 'www.reddit.com',
                 'mobile.reddit.com', 'google.com', 'm.google.com',
                 'www.google.com', 'mobile.google.com', 'twitter.com',
                 'm.twitter.com', 'www.twitter.com', 'mobile.twitter.com'
                ]))

    def test__on_taskrun(self):
        """ SiteBlock.on_taskrun: adds domain blocks to hosts file.
            """
        domains = [
            'google.com', 'm.google.com', 'www.google.com',
            'mobile.google.com', 'twitter.com', 'm.twitter.com',
            'www.twitter.com', 'mobile.twitter.com'
        ]

        self.plugin.domains = set(domains)
        self.plugin.on_taskrun(self.task)

        self.assertEqual(open(self.plugin.hosts_file, 'r').read(),
                          _BLKD_HOST_FILE_DATA)

    def test__on_taskend(self):
        """ SiteBlock.on_taskend: removes domain blocks from hosts file.
            """
        # write backup hosts file which is used to replace blocked one
        open(self.backup_hosts_file, 'w', 0).write(_HOST_FILE_DATA)

        # write "blocked" hosts file
        open(self.plugin.hosts_file, 'w', 0).write(_BLKD_HOST_FILE_DATA)

        domains = [
            'google.com', 'm.google.com', 'www.google.com',
            'mobile.google.com', 'twitter.com', 'm.twitter.com',
            'www.twitter.com', 'mobile.twitter.com'
        ]

        self.plugin.domains = set(domains)
        self.plugin.on_taskend(self.task)

        self.assertEqual(open(self.plugin.hosts_file, 'r').read(),
                          _HOST_FILE_DATA)

        # backup removed
        self.assertFalse(os.path.isfile(self.backup_hosts_file))
