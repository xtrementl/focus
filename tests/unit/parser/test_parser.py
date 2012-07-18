# TODO: expand these tests to check more edge cases in parsing grammars.

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

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

_TEST_DUPEBLK_DATA = """header_value {
    option "12345";
    block_name {
        option "name";
        option "name 2";
    }
    block_name2 {
        option "name 4";
    }
    block_name2 {
        option "name 5";
    }
    block_name {
        option "name 3";
    }
    block_name3 {
        option "name 6";
    }
}
"""


class TestSettingParser(FocusTestCase):
    def _get_expected_tokens(self):
        return [
            'header_value', '{', 'option', '12345', ';', 'block_name', '{',
            'option', 'name', ';', 'option', 'name 2', ';', '}', '}'
        ]

    def _get_nonblock_options(self, *names):
        ast = [None, [], []]

        for name in names:
            ast[1].append([name, ['test_val1', 'test_val2']])

        return ast

    def _get_block(self, block_name):
        ast = [None, [], []]
        block_map = {block_name: 0}
        ast[2].append([block_name, []])

        return ast, block_map

    def _get_block_options(self, block_name, *names):
        ast, block_map = self._get_block(block_name)
        for name in names:
            ast[2][0][1].append([name, ['test_val1', 'test_val2']])

        return ast, block_map

    def setUp(self):
        super(TestSettingParser, self).setUp()
        self.setup_dir()
        self.stream = StringIO(_TEST_DATA)
        self.parser = parser.SettingParser()
        self.parser._lexer = parser.SettingLexer()
        self.parser._lexer.readstream(self.stream)

    def tearDown(self):
        self.parser = None
        super(TestSettingParser, self).tearDown()

    def test___reset(self):
        """ SettingParser._reset: resets attributes.
            """
        self.parser._filename = 'OMGS'
        self.parser._block_map = {'a': 1, 'b': 2}
        self.parser._ast = ['header', ['xx'], ['xx']]
        self.parser._reset()
        self.assertIsNone(self.parser._filename)
        self.assertEqual(self.parser._block_map, {})
        self.assertIsNone(self.parser._ast[0])
        self.assertEqual(self.parser._ast[1], [])
        self.assertEqual(self.parser._ast[2], [])

    def test___get_token(self):
        """ SettingParser._get_token: returns expected tokens.
            """
        expected = self._get_expected_tokens()
        for token in expected:
            self.assertEqual(self.parser._get_token(), token)

        # stack empty
        with self.assertRaises(parser.ParseError):
            self.parser._get_token()

    def test___lookahead_token(self):
        """ SettingParser._lookahead_token: returns expected tokens without
            emptying stack.
            """
        expected = self._get_expected_tokens()
        size = len(expected)

        for idx in range(size):
            token = expected[idx]
            self.assertEqual(self.parser._lookahead_token(count=idx + 1),
                             token)

        # no tokens removed
        self.assertNotEqual(self.parser._lexer._tokens, expected)

    def testValid___expect_token(self):
        """ SettingParser._expect_token: expects next token, compares
            correctly.
            """
        expected = self._get_expected_tokens()

        for token in expected:
            self.parser._expect_token(token)

        # empty stack, should raise
        with self.assertRaises(parser.ParseError):
            self.parser._expect_token('...')

    def testInvalid___expect_token(self):
        """ SettingParser._expect_token: expects next token, compare fails.
            """
        expected = self._get_expected_tokens()
        self.parser._expect_token(expected[0])
        self.parser._expect_token(expected[1])
        with self.assertRaises(parser.ParseError):
            self.parser._expect_token('invalid')

    def testEmpty___expect_empty(self):
        """ SettingParser._expect_empty: expects stack empty, success.
            """
        self.parser._lexer._tokens = []
        self.parser._expect_empty()

    def testNotEmpty___expect_empty(self):
        """ SettingParser._expect_empty: expects stack empty, fails.
            """
        with self.assertRaises(parser.ParseError):
            self.parser._expect_empty()

    def testNormal___rule_container(self):
        """ SettingParser._rule_container: parses container rule.
            """
        self.assertEqual(self.parser._rule_container(),
            ['header_value',
             [['option', ['12345']]],
             [['block_name', [['option', ['name']], ['option', ['name 2']]]]]
            ]
        )

    def testDupeBlock___rule_container(self):
        """ SettingParser._rule_container: parses container rule with
            duplicate blocks and dedupes them.
            """

        self.stream = StringIO(_TEST_DUPEBLK_DATA)
        self.parser = parser.SettingParser()
        self.parser._lexer = parser.SettingLexer()
        self.parser._lexer.readstream(self.stream)

        self.assertEqual(self.parser._rule_container(),
            ['header_value',
             [['option', ['12345']]],
             [['block_name', [['option', ['name 3']]]],
              ['block_name2', [['option', ['name 5']]]],
              ['block_name3', [['option', ['name 6']]]]]
            ]
        )

    def test___rule_option(self):
        """ SettingParser._rule_option: parses option rule.
            """
        # single-value
        self.parser._lexer._tokens = [(1, 'option'), (1, 'name'), (1, ';')]
        self.assertEqual(self.parser._rule_option(), ['option', ['name']])

        # multi-value
        self.parser._lexer._tokens = [(1, 'option'), (1, 'name'), (1, ','),
                                      (1, 'name 2'), (1, ';')]
        self.assertEqual(self.parser._rule_option(), ['option',
                         ['name', 'name 2']])

        # missing semicolon
        self.parser._lexer._tokens = [(1, 'option'), (1, 'name')]
        with self.assertRaises(parser.ParseError):
            self.parser._rule_option()

        # missing second value
        self.parser._lexer._tokens = [(1, 'option'), (1, 'name'), (1, ','),
                                      (1, ';')]
        with self.assertRaises(parser.ParseError):
            self.parser._rule_option()

    def test___rule_value(self):
        """ SettingParser._rule_value: parses value rule.
            """
        # single-value
        self.parser._lexer._tokens = [(1, 'name')]
        self.assertEqual(self.parser._rule_value(), ['name'])

        # multi-value
        self.parser._lexer._tokens = [(1, 'name'), (1, ','), (1, 'name 2')]
        self.assertEqual(self.parser._rule_value(), ['name', 'name 2'])

        # missing value after comma
        self.parser._lexer._tokens = [(1, 'name'), (1, ',')]
        with self.assertRaises(parser.ParseError):
            self.parser._rule_value()

    def test___rule_block(self):
        """ SettingParser._rule_block: parses block rule.
            """
        # single-value
        self.parser._lexer._tokens = [(1, 'block_name'), (1, '{'),
            (2, 'option'), (2, 'name'), (2, ';'), (3, '}')]
        self.assertEqual(self.parser._rule_block(), ['block_name',
                                                    [['option', ['name']]]])

        # multi-value
        self.parser._lexer._tokens = [(1, 'block_name'), (1, '{'),
            (2, 'option'), (2, 'name'), (2, ','), (2, 'name 2'), (2, ';'),
            (3, '}')]
        self.assertEqual(self.parser._rule_block(),
            ['block_name', [['option', ['name', 'name 2']]]])

        # missing value after comma
        self.parser._lexer._tokens = [(1, 'block_name'), (1, '{'),
            (2, 'option'), (2, 'name'), (3, '}')]
        with self.assertRaises(parser.ParseError):
            self.parser._rule_block()

    def test__read(self):
        """ SettingParser.read: reads data from file, parses correctly.
            """
        filename = self.make_file(_TEST_DATA)
        self.parser.read(filename)
        self.assertEqual(self.parser._filename, filename)
        self.assertEqual(self.parser._ast[0], 'header_value')
        self.assertEqual(self.parser._ast[1],
            [['option', ['12345']]])
        self.assertEqual(self.parser._ast[2],
            [['block_name', [['option', ['name']], ['option', ['name 2']]]]])

    def test__readstream(self):
        """ SettingParser.readstream: read data from stream, parses correctly.
            """
        new_stream = StringIO(_TEST_DATA)
        self.parser = parser.SettingParser()
        self.parser.readstream(new_stream)

        self.assertEqual(self.parser._ast[0], 'header_value')
        self.assertEqual(self.parser._ast[1],
            [['option', ['12345']]])
        self.assertEqual(self.parser._ast[2],
            [['block_name', [['option', ['name']], ['option', ['name 2']]]]])

    def test__write(self):
        """ SettingParser.write: writes to file.
            """
        new_stream = StringIO(_TEST_DATA)
        self.parser = parser.SettingParser()
        self.parser.readstream(new_stream)

        filename = self.make_file()
        self.assertTrue(self.parser.write(filename, 'header_value'))
        self.assertTrue(self.parser._filename, filename)
        self.assertEqual(open(filename, 'r').read(), _TEST_DATA)

    def test__writestream(self):
        """ SettingParser.writestream: writes to stream.
            """
        new_stream = StringIO(_TEST_DATA)
        self.parser = parser.SettingParser()
        self.parser.readstream(new_stream)

        filename = self.make_file()
        with open(filename, 'w', 0) as f:
            self.assertTrue(self.parser.writestream(f, 'header_value'))
        self.assertEqual(open(filename, 'r').read(), _TEST_DATA)

    def testNonBlockNoValue__add_option(self):
        """ SettingParser.add_option: adding non-block option, no value
            provided.
            """
        self.parser = parser.SettingParser()
        with self.assertRaises(ValueError):
            self.parser.add_option(None, 'option_name')

    def testNonBlockSingleValue__add_option(self):
        """ SettingParser.add_option: adding non-block option, single value
            provided.
            """
        self.parser = parser.SettingParser()
        self.parser.add_option(None, 'option_name', 'value1')
        self.assertEqual(self.parser._ast[1], [['option_name', ['value1']]])

    def testNonBlockMultiValue__add_option(self):
        """ SettingParser.add_option: adding non-block option, multiple values
            provided.
            """
        self.parser = parser.SettingParser()
        self.parser.add_option(None, 'option_name', 'value1')
        self.parser.add_option(None, 'option_name', 'value1')
        self.parser.add_option(None, 'other_opt_name', 'value2')
        self.assertEqual(self.parser._ast[1], [
            ['option_name', ['value1']],
            ['option_name', ['value1']],
            ['other_opt_name', ['value2']]
        ])

    def testBlockNotExistNoValue__add_option(self):
        """ SettingParser.add_option: adding option for for non-existing
            block.
            """
        self.parser = parser.SettingParser()
        with self.assertRaises(ValueError):
            self.parser.add_option('block_name', 'option_name')

    def testBlockExistNoValue__add_option(self):
        """ SettingParser.add_option: adding option to existing block, no
            value provided.
            """
        self.parser = parser.SettingParser()

        res = self._get_block_options('test', 'opt')
        self.parser._ast, self.parser._block_map = res
        with self.assertRaises(ValueError):
            self.parser.add_option('test', 'opt')

    def testBlockExistSingleValue__add_option(self):
        """ SettingParser.add_option: adding option to existing block, single
            value provided.
            """
        self.parser = parser.SettingParser()
        res = self._get_block('test')
        self.parser._ast, self.parser._block_map = res

        self.parser.add_option('test', 'option_name', 'value1')
        self.assertEqual(self.parser._ast[2], [
            ['test', [
                ['option_name', ['value1']]
            ]]
        ])

    def testBlockExistMultiValue__add_option(self):
        """ SettingParser.add_option: adding option to existing block, multiple
            value provided.
            """
        self.parser = parser.SettingParser()
        res = self._get_block('test')
        self.parser._ast, self.parser._block_map = res

        self.parser.add_option('test', 'option_name', 'value1')
        self.parser.add_option('test', 'option_name', 'value1', 'value2')
        self.parser.add_option('test', 'other_opt_name', 'value2')
        self.assertEqual(self.parser._ast[2], [
            ['test', [
                ['option_name', ['value1']],
                ['option_name', ['value1', 'value2']],
                ['other_opt_name', ['value2']]
            ]]
        ])

    def testBlockNotExist__remove_option(self):
        """ SettingParser.remove_option: removing option from non-existent
            block.
            """
        self.parser = parser.SettingParser()
        with self.assertRaises(ValueError):
            self.parser.remove_option('non_exist', 'option_name')

    def testReadFileBlockNotExist__remove_option(self):
        """ SettingParser.remove_option: removing option from existent
            block after reading from file.
            """
        filename = self.make_file()
        with open(filename, 'w', 0) as f:
            f.write(_TEST_DATA)

        self.parser = parser.SettingParser(filename)
        self.parser.remove_option('block_name', 'option')
        self.parser.remove_option('block_name', 'option')

        with self.assertRaises(ValueError):
            self.parser.remove_option('block_name', 'option')

    def testNonBlockOptionExist__remove_option(self):
        """ SettingParser.remove_option: removing option.
            """
        self.parser = parser.SettingParser()

        self.parser._ast = self._get_nonblock_options('opt')
        self.parser.remove_option(None, 'opt')
        self.assertEqual(self.parser._ast[1], [])

    def testBlockExistOptionExist__remove_option(self):
        """ SettingParser.remove_option: removing option from an existing
            block.
            """
        self.parser = parser.SettingParser()

        res = self._get_block_options('test', 'opt')
        self.parser._ast, self.parser._block_map = res
        self.parser.remove_option('test', 'opt')
        self.assertEqual(self.parser._ast[2], [['test', []]])

    def testBlockExistOptionNotExist__remove_option(self):
        """ SettingParser.remove_option: removing non-existent option from an
            existing block.
            """
        self.parser = parser.SettingParser()

        res = self._get_block_options('test', 'opt')
        self.parser._ast, self.parser._block_map = res
        with self.assertRaises(ValueError):
            self.parser.remove_option('test', 'non_exist')

    def testNonBlockOptionNotExist__remove_option(self):
        """ SettingParser.remove_option: removing non-existent option.
            """
        self.parser = parser.SettingParser()
        self.parser._ast = self._get_nonblock_options()
        with self.assertRaises(ValueError):
            self.parser.remove_option(None, 'non_exist')

        self.parser._ast = self._get_nonblock_options('test')
        with self.assertRaises(ValueError):
            self.parser.remove_option(None, 'non_exist')

    def testExist__add_block(self):
        """ SettingParser.add_block: adding block that already exists.
            """
        self.parser = parser.SettingParser()
        res = self._get_block('test')
        self.parser._ast, self.parser._block_map = res
        with self.assertRaises(ValueError):
            self.parser.add_block('test')

    def testNotExist__add_block(self):
        """ SettingParser.add_block: adding block that doesn't exist.
            """
        self.parser = parser.SettingParser()
        self.parser.add_block('test')

        ast, _ = self._get_block('test')
        self.assertEqual(self.parser._ast[2], ast[2])

    def testExist__remove_block(self):
        """ SettingParser.remove_block: removing existing block.
            """
        self.parser = parser.SettingParser()

        # existing block with options, then existing block no options
        args = [('test', 'opt1'), ('test',)]
        for arg in args:
            res = self._get_block_options(*arg)
            self.parser._ast, self.parser._block_map = res
            self.parser.remove_block('test')
            self.assertEqual(self.parser._ast[2], [])

    def testNotExist__remove_block(self):
        """ SettingParser.remove_block: removing non-existent block.
            """
        self.parser = parser.SettingParser()
        with self.assertRaises(ValueError):
            self.parser.remove_block('non_exist')

    def test__filename(self):
        """ SettingParser.filename (property): returns correct values.
            """
        self.parser = parser.SettingParser()
        self.assertIsNone(self.parser.filename)  # not set

        self.parser._filename = 'test'
        self.assertEqual(self.parser.filename, 'test')

    def test__header(self):
        """ SettingParser.header (property): returns correct values.
            """
        # not set
        self.parser = parser.SettingParser()
        self.assertIsNone(self.parser.header)

        self.parser._ast = ['test', [], []]
        self.assertEqual(self.parser.header, 'test')

    def test__options(self):
        """ SettingParser.options (property): returns correct values.
            """
        # not set
        self.parser = parser.SettingParser()
        self.assertEqual([], list(self.parser.options))  # empty generator

        self.parser._ast = self._get_nonblock_options('opt_test')
        self.assertEqual(list(self.parser.options), self.parser._ast[1])

    def test__blocks(self):
        """ SettingParser.blocks (property): returns correct values.
            """
        # not set
        self.parser = parser.SettingParser()
        self.assertEqual([], list(self.parser.blocks))  # empty generator

        res = self._get_block_options('test', 'opt')
        self.parser._ast, self.parser._block_map = res
        self.assertEqual(list(self.parser.blocks), self.parser._ast[2])
