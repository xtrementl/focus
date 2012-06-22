from focus import parser
from focus_unittest import FocusTestCase


_TEST_DATA = """header_value {
    option "12345";
    block_name {
        option "name";
        option "name 2";
    }
}
"""


class TestParser(FocusTestCase):
    def setUp(self):
        super(TestParser, self).setUp()
        self.setup_dir()
        self.test_config = self.make_file(_TEST_DATA)

    def tearDown(self):
        self.clean_paths(self.test_config)
        super(TestParser, self).tearDown()

    def test__parse_config(self):
        """ parser.parse_config: check for proper errors raised.
            """
        # raises, missing file
        with self.assertRaises(parser.ParseError):
            parser.parse_config('non_exist', 'header-name')

        # raises, good file, mismatched header value
        with self.assertRaises(parser.ParseError):
            parser.parse_config(self.test_config, 'wrong_header_value')

        # all good.. returns parser
        self.assertIsInstance(parser.parse_config(self.test_config,
                                                  'header_value'),
                              parser.SettingParser)
