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


class TestSettingLexer(FocusTestCase):
    def _get_expected_tokens(self):
        return [
            (1, 'header_value'), (1, '{'), (2, 'option'), (2, '12345'),
            (2, ';'), (3, 'block_name'), (3, '{'), (4, 'option'), (4, 'name'),
            (4, ';'), (5, 'option'), (5, 'name 2'), (5, ';'), (6, '}'),
            (7, '}')
        ]

    def setUp(self):
        super(TestSettingLexer, self).setUp()
        self.setup_dir()
        self.stream = StringIO(_TEST_DATA)
        self.lexer = parser.SettingLexer()

    def tearDown(self):
        self.lexer = None
        super(TestSettingLexer, self).tearDown()

    def test___reset_token(self):
        """ SettingLexer._reset_token: resets correct token info.
            """

        self.lexer._token_info['line_no'] = 999
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._reset_token()
        self.assertEqual(self.lexer._token_info['line_no'], 1)
        self.assertEqual(self.lexer._token_info['chars'], [])

    def test___new_token(self):
        """ SettingLexer._new_token: adds new token.
            """

        # correct defaults
        self.lexer._token_info['line_no'] = 1234
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._new_token()
        self.assertEqual(self.lexer._tokens, [(1234, 'abc')])
        self.assertEqual(self.lexer._token_info['chars'], [])

        # correct line_no default
        self.lexer._token_info['line_no'] = 999
        self.lexer._new_token(chars=['d', 'e', 'f'])
        self.assertEqual(self.lexer._tokens,
                         [(1234, 'abc'),
                          (999, 'def')])
        self.assertEqual(self.lexer._token_info['chars'], [])

        # correct chars default
        self.lexer._token_info['chars'] = ['g', 'h', 'i']
        self.lexer._new_token(line_no=1212)
        self.assertEqual(self.lexer._tokens,
                         [(1234, 'abc'),
                          (999, 'def'),
                          (1212, 'ghi')])
        self.assertEqual(self.lexer._token_info['chars'], [])

    def testAppendChar___process_newline(self):
        """ SettingLexer._process_newline: appends newline character.
            """

        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._process_newline('\n')
        self.assertEqual(self.lexer._token_info['chars'], ['\n'])
        self.assertEqual(self.lexer._token_info['line_no'], 2)
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_STRING)

    def testNewToken___process_newline(self):
        """ SettingLexer._process_newline: adds new token.
            """

        # comment state, appends token, switches to token state
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._state_info['state'] = self.lexer.ST_COMMENT
        self.lexer._process_newline('\n')
        self.assertEqual(self.lexer._tokens, [(1, 'abc')])
        self.assertEqual(self.lexer._token_info['line_no'], 2)
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_TOKEN)

        # token state, appends token, keeps same state
        self.lexer._token_info['chars'] = ['d', 'e', 'f']
        self.lexer._state_info['state'] = self.lexer.ST_TOKEN
        self.lexer._process_newline('\n')
        self.assertEqual(self.lexer._tokens, [(1, 'abc'), (2, 'def')])
        self.assertEqual(self.lexer._token_info['line_no'], 3)
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_TOKEN)

    def testEscapedMatchQuote___process_string(self):
        """ SettingLexer._process_string: handles escaped matched quote.
            """

        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._state_info['last_quote'] = '"'
        self.lexer._token_info['chars'] = [self.lexer.ESCAPE]
        self.lexer._process_string('"')
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'], ['"'])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_STRING)

    def testNonEscapedMatchQuote___process_string(self):
        """ SettingLexer._process_string: handles end of string.
            """

        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._state_info['last_quote'] = '"'
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._process_string('"')
        self.assertEqual(self.lexer._tokens, [(1, 'abc')])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_TOKEN)

    def testDoubleEscapedMatchQuote___process_string(self):
        """ SettingLexer._process_string: handles end of string with prior
            double-escape.
            """

        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._state_info['last_quote'] = '"'
        self.lexer._state_info['double_esc'] = True
        self.lexer._token_info['chars'] = ['a', 'b', 'c', self.lexer.ESCAPE]
        self.lexer._process_string('"')
        self.assertEqual(self.lexer._tokens, [(1, 'abc')])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_TOKEN)

    def testNonMatchQuote___process_string(self):
        """ SettingLexer._process_string: handles non-matching quote.
            """

        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._state_info['last_quote'] = '"'
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._process_string("'")
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'],
                         ['a', 'b', 'c', "'"])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_STRING)

    def testEscape___process_string(self):
        """ SettingLexer._process_string: handles escape character.
            """

        # double-escaped
        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._state_info['double_esc'] = False
        self.lexer._token_info['chars'] = [self.lexer.ESCAPE]
        self.lexer._process_string(self.lexer.ESCAPE)
        self.assertEqual(self.lexer._tokens, [])
        self.assertTrue(self.lexer._state_info['double_esc'])
        self.assertEqual(self.lexer._token_info['chars'], [self.lexer.ESCAPE])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_STRING)

        # single-escape char
        self.lexer._token_info['chars'] = []
        self.lexer._state_info['double_esc'] = False
        self.lexer._process_string(self.lexer.ESCAPE)
        self.assertEqual(self.lexer._tokens, [])
        self.assertFalse(self.lexer._state_info['double_esc'])
        self.assertEqual(self.lexer._token_info['chars'], [self.lexer.ESCAPE])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_STRING)

    def testNonQuote___process_string(self):
        """ SettingLexer._process_string: handles non-quote character.
            """

        self.lexer._state_info['state'] = self.lexer.ST_STRING
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._process_string('d')
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'],
                         ['a', 'b', 'c', 'd'])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_STRING)

    def testEscapedWhitespaceOrToken___process_tokens(self):
        """ SettingLexer._process_tokens: handles escaped whitespace/token
            character.
            """

        # whitespace
        self.lexer._token_info['chars'] = [self.lexer.ESCAPE]
        self.lexer._process_tokens(' ')
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'], [' '])

        # token
        self.lexer._token_info['chars'] = [self.lexer.ESCAPE]
        self.lexer._process_tokens(self.lexer.TOKENS[:1])
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'],
                         [self.lexer.TOKENS[:1]])

    def testNonEscapedWhitespaceOrToken___process_tokens(self):
        """ SettingLexer._process_tokens: handles non-escaped whitespace/token
            character.
            """

        # whitespace
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._process_tokens(' ')
        self.assertEqual(self.lexer._tokens, [(1, 'abc')])
        self.assertEqual(self.lexer._token_info['chars'], [])

        # token
        self.lexer._token_info['chars'] = ['d', 'e', 'f']
        self.lexer._process_tokens(self.lexer.TOKENS[:1])
        self.assertEqual(self.lexer._tokens,
                        [(1, 'abc'),
                         (1, 'def'),
                         (1, self.lexer.TOKENS[:1])])
        self.assertEqual(self.lexer._token_info['chars'], [])

    def testCommentStart___process_tokens(self):
        """ SettingLexer._process_tokens: handles comment start character.
            """

        test_chars = ['a', 'b', 'c']
        self.lexer._state_info['state'] = self.lexer.ST_TOKEN
        self.lexer._token_info['chars'] = test_chars
        self.lexer._process_tokens('#')
        self.assertEqual(self.lexer._tokens, [
            (self.lexer._token_info['line_no'], ''.join(test_chars))
        ])
        self.assertEqual(self.lexer._token_info['chars'], [])
        self.assertEqual(self.lexer._state_info['state'],
                         self.lexer.ST_COMMENT)

    def testEscapedQuote___process_tokens(self):
        """ SettingLexer._process_tokens: handles escaped quote character.
            """

        self.lexer._token_info['chars'] = [self.lexer.ESCAPE]
        self.lexer._process_tokens('"')
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'], ['"'])

    def testNonEscapedQuote___process_tokens(self):
        """ SettingLexer._process_tokens: handles non-escaped quote character.
            """

        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._state_info['state'] = self.lexer.ST_TOKEN
        self.lexer._state_info['last_quote'] = None

        self.lexer._process_tokens('"')
        self.assertEqual(self.lexer._tokens, [(1, 'abc')])
        self.assertEqual(self.lexer._token_info['chars'], [])

        self.assertEqual(self.lexer._state_info['state'], self.lexer.ST_STRING)
        self.assertEqual(self.lexer._state_info['last_quote'], '"')

    def testNonTokenChar___process_tokens(self):
        """ SettingLexer._process_tokens: handles regular non-token character.
            """

        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.lexer._process_tokens('d')
        self.assertEqual(self.lexer._tokens, [])
        self.assertEqual(self.lexer._token_info['chars'], ['a', 'b', 'c', 'd'])

    def test___tokenize(self):
        """ SettingLexer._tokenize: scans and tokenizes the provided data.
            """
        self.lexer._tokenize(self.stream)
        self.assertEqual(self.lexer._tokens, self._get_expected_tokens())

    def test__read(self):
        """ SettingLexer.read: scans the provided file.
            """
        filename = self.make_file(_TEST_DATA)
        self.lexer.read(filename)
        self.assertEqual(self.lexer._tokens, self._get_expected_tokens())

        # check that second read correctly resets and re-reads
        self.lexer.read(filename)
        self.assertEqual(self.lexer._tokens, self._get_expected_tokens())

    def test__readstream(self):
        """ SettingLexer.readstream: scans the provided stream.
            """
        # test current readstream
        self.lexer.readstream(self.stream)
        self.assertEqual(self.lexer._tokens, self._get_expected_tokens())

        # check that second read correctly resets and re-reads
        new_stream = StringIO(_TEST_DATA)
        self.lexer.readstream(new_stream)
        self.assertEqual(self.lexer._tokens, self._get_expected_tokens())

    def test__get_token(self):
        """ SettingLexer.get_token: pops next token off the internal stack.
            """
        self.lexer.readstream(self.stream)

        expected = self._get_expected_tokens()
        for token in expected:
            self.assertEqual(self.lexer.get_token(), token)

        # stack empty, check for None returned
        self.assertIsNone(self.lexer.get_token())

    def test__push_token(self):
        """ SettingLexer.push_token: pushes token onto internal stack.
            """
        # push test tokens on stack in reverse order
        expected = self._get_expected_tokens()
        for line_no, token in reversed(expected):
            self.lexer.push_token(line_no, token)

        # compare pushed tokens to expected
        for idx, token in enumerate(self.lexer._tokens):
            self.assertEqual(token, expected[idx])

    def testGetter___last_quote(self):
        """ SettingLexer._last_quote (property): returns last quote
            encountered.
            """
        self.lexer._state_info['last_quote'] = '"'
        self.assertEqual(self.lexer._last_quote, '"')

    def testSetter___last_quote(self):
        """ SettingLexer._last_quote (property): sets last quote
            encountered.
            """
        self.lexer._last_quote = '"'
        self.assertEqual(self.lexer._state_info['last_quote'], '"')

    def testGetter___double_escaped(self):
        """ SettingLexer._double_escaped (property): returns if double escape
            encountered.
            """
        self.lexer._state_info['double_esc'] = True
        self.assertTrue(self.lexer._double_escaped)
        self.lexer._state_info['double_esc'] = False
        self.assertFalse(self.lexer._double_escaped)

    def testSetter___double_escaped(self):
        """ SettingLexer._double_escaped (property): sets if double escape
            encountered.
            """
        self.lexer._double_escaped = True
        self.assertTrue(self.lexer._state_info['double_esc'])
        self.lexer._double_escaped = False
        self.assertFalse(self.lexer._state_info['double_esc'])

    def testGetter___state(self):
        """ SettingLexer._state (property): returns lexer state.
            """

        for state in (self.lexer.ST_STRING, self.lexer.ST_COMMENT,
                      self.lexer.ST_TOKEN):
            self.lexer._state_info['state'] = state
            self.assertEqual(self.lexer._state, state)

    def testSetter___state(self):
        """ SettingLexer._state (property): resets to a lexer state.
            """

        for state in (self.lexer.ST_STRING, self.lexer.ST_COMMENT,
                      self.lexer.ST_TOKEN):
            self.lexer._state_info['state'] = None
            self.lexer._state_info['last_quote'] = '"'
            self.lexer._state_info['double_esc'] = True

            self.lexer._state = state
            self.assertEqual(self.lexer._state_info['state'], state)
            self.assertIsNone(self.lexer._state_info['last_quote'])
            self.assertFalse(self.lexer._state_info['double_esc'])

    def testGetter___token_chars(self):
        """ SettingLexer._token_chars (property): returns current token chars.
            """

        test_chars = ['a', 'b', 'c']
        self.lexer._token_info['chars'] = test_chars
        self.assertEqual(self.lexer._token_chars, test_chars)

    def testSetter___token_chars(self):
        """ SettingLexer._token_chars (property): sets current token chars.
            """
        test_chars = ['a', 'b', 'c']
        self.lexer._token_chars = test_chars
        self.assertEqual(self.lexer._token_info['chars'], test_chars)

    def testGetter___line_no(self):
        """ SettingLexer._line_no (property): returns current line number.
            """

        self.lexer._token_info['line_no'] = 2
        self.assertEqual(self.lexer._line_no, 2)
        self.lexer._token_info['line_no'] = 99
        self.assertEqual(self.lexer._line_no, 99)

    def testSetter___line_no(self):
        """ SettingLexer._line_no (property): sets current line number.
            """

        self.lexer._line_no = 2
        self.assertEqual(self.lexer._token_info['line_no'], 2)
        self.lexer._line_no = 99
        self.assertEqual(self.lexer._token_info['line_no'], 99)

    def test___escaped(self):
        """ SettingLexer._escaped (property): returns if prior char is escape.
            """

        self.lexer._token_info['chars'] = ['a', 'b', 'c', self.lexer.ESCAPE]
        self.assertTrue(self.lexer._escaped)
        self.lexer._token_info['chars'] = ['a', 'b', 'c']
        self.assertFalse(self.lexer._escaped)

    def testStream__filename(self):
        """ SettingLexer.filename (property): ``None`` returned for scanned
            stream.
            """
        self.lexer.readstream(self.stream)
        self.assertIsNone(self.lexer.filename)

    def testFile__filename(self):
        """ SettingLexer.filename (property): filename returned for scanned
            file.
            """
        self.assertIsNone(self.lexer.filename)  # nothing read

        filename = self.make_file(_TEST_DATA)
        self.lexer.read(filename)
        self.assertIsNotNone(self.lexer.filename)

    def test__tokens(self):
        """ SettingLexer.tokens (property): returns correct values for tokens.
            """
        self.lexer.readstream(self.stream)
        self.assertEqual(list(self.lexer.tokens), self._get_expected_tokens())
