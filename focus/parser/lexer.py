""" This module provides a lexical scanner component for the `parser` package.
    """


class SettingLexer(object):
    """ Simple lexical scanner that tokenizes a stream of configuration data.
        See ``SettingParser`` for further information about grammar rules and
        specifications.

        Example Usage::

            >>> lexer = SettingLexer("task.cfg")
            >>> [(line_no, token) for line_no, token in lexer.tokens]
            [(1, 'task'), (1, '{'), (2, 'duration'), (2, '30'), (2, ';'),
            (3, '}')]

            >>> lexer = SettingLexer()
            >>> lexer.read("task.cfg")
            True
            >>> [(line_no, token) for line_no, token in lexer.tokens]
            [(1, 'task'), (1, '{'), (2, 'duration'), (2, '30'), (2, ';'),
            (3, '}')]

            >>> lexer = SettingLexer()
            >>> with open('task.cfg', 'r') as f:
            ...     lexer.readstream(f)
            >>> [(line_no, token) for line_no, token in lexer.tokens]
            [(1, 'task'), (1, '{'), (2, 'duration'), (2, '30'), (2, ';'),
            (3, '}')]

        """

    # character classes
    WHITESPACE = ' \n\r\t'
    COMMENT_START = '#'
    NEWLINES = '\n\r'
    TOKENS = '{},;'
    QUOTES = '\'"'
    ESCAPE = '\\'
    SPACE = ' '

    # lexer states
    ST_TOKEN = 1
    ST_STRING = 2
    ST_COMMENT = 3

    def __init__(self, filename=None):
        self._tokens = []
        self._filename = None
        self._token_info = {}
        self._state_info = {}

        self._reset_token()
        self._state = self.ST_TOKEN

        if filename:
            self.read(filename)

    def _reset_token(self):
        """ Resets current token information.
            """
        self._token_info = {'line_no': 1,
                            'chars': []}

    def _new_token(self, chars=None, line_no=None):
        """ Appends new token to token stream.

            `chars`
                List of token characters. Defaults to current token list.
            `line_no`
                Line number for token. Defaults to current line number.
            """

        if not line_no:
            line_no = self._line_no

        if not chars:
            chars = self._token_chars

        if chars:
            # add new token
            self._tokens.append((line_no, ''.join(chars)))
            self._token_chars = []  # clear values

    def _process_newline(self, char):
        """ Process a newline character.
            """

        state = self._state

        # inside string, just append char to token
        if state == self.ST_STRING:
            self._token_chars.append(char)
        else:
            # otherwise, add new token
            self._new_token()

        self._line_no += 1  # update line counter

        # finished with comment
        if state == self.ST_COMMENT:
            self._state = self.ST_TOKEN

    def _process_string(self, char):
        """ Process a character as part of a string token.
            """

        if char in self.QUOTES:
            # end of quoted string:
            #   1) quote must match original quote
            #   2) not escaped quote (e.g. "hey there" vs "hey there\")
            #   3) actual escape char prior (e.g. "hey there\\")

            if (char == self._last_quote and
                    not self._escaped or self._double_escaped):

                # store token
                self._new_token()
                self._state = self.ST_TOKEN
                return  # skip adding token char

        elif char == self.ESCAPE:
            # escape character:
            #   double escaped if prior char was escape (e.g. "hey \\ there")

            if not self._double_escaped:
                self._double_escaped = self._escaped

        else:
            self._double_escaped = False

        self._token_chars.append(char)

    def _process_tokens(self, char):
        """ Process a token character.
            """

        if (char in self.WHITESPACE or char == self.COMMENT_START or
                char in self.QUOTES or char in self.TOKENS):

            add_token = True

            # escaped chars, keep going
            if char == self.SPACE or char in self.TOKENS:
                if self._escaped:
                    add_token = False

            # start of comment
            elif char == self.COMMENT_START:
                self._state = self.ST_COMMENT

            # start of quoted string
            elif char in self.QUOTES:
                if self._escaped:
                    # escaped, keep going
                    add_token = False

                else:
                    self._state = self.ST_STRING
                    self._last_quote = char  # store for later quote matching

            if add_token:
                # store token
                self._new_token()

                if char in self.TOKENS:
                    # store char as a new token
                    self._new_token([char])

                return  # skip adding token char

        self._token_chars.append(char)

    def _tokenize(self, stream):
        """ Tokenizes data from the provided string.

            ``stream``
                ``File``-like object.
            """

        self._tokens = []
        self._reset_token()
        self._state = self.ST_TOKEN

        for chunk in iter(lambda: stream.read(8192), ''):
            for char in chunk:
                if char in self.NEWLINES:
                    self._process_newline(char)

                else:
                    state = self._state

                    if state == self.ST_STRING:
                        self._process_string(char)

                    elif state == self.ST_TOKEN:
                        self._process_tokens(char)

    def read(self, filename):
        """ Reads the file specified and tokenizes the data for parsing.
            """

        try:
            with open(filename, 'r') as _file:
                self._filename = filename
                self.readstream(_file)
            return True

        except IOError:
            self._filename = None
            return False

    def readstream(self, stream):
        """ Reads the file specified and tokenizes the data for parsing.

            ``stream``
                ``File``-like object.
            """

        self._tokenize(stream)

    def get_token(self):
        """ Pops the next element off the internal token stack and returns.

            Returns tuple (line_no, token) or ``None``.
            """

        if not self._tokens:
            return None
        else:
            return self._tokens.pop(0)

    def push_token(self, line_no, token):
        """ Pushes a token back on the internal token stack.
            """
        self._tokens.insert(0, (line_no, token))

    @property
    def _last_quote(self):
        """ Gets the last quote character encountered.
            """
        return self._state_info['last_quote']

    @_last_quote.setter
    def _last_quote(self, value):
        """ Sets the last quote character encountered.
            """
        self._state_info['last_quote'] = value

    @property
    def _double_escaped(self):
        """ Gets if last escape character was escaped.
            """
        return bool(self._state_info['double_esc'])

    @_double_escaped.setter
    def _double_escaped(self, value):
        """ Sets if last escape character was escaped.
            """

        self._state_info['double_esc'] = value

    @property
    def _state(self):
        """ Gets the current state of the lexer.
            """

        return self._state_info['state']

    @_state.setter
    def _state(self, value):
        """ Sets the current state of the lexer.
            """
        self._state_info = {'state': value,
                            'last_quote': None,
                            'double_esc': False}

    @property
    def _line_no(self):
        """ Gets the current line number.
            """
        return self._token_info['line_no']

    @_line_no.setter
    def _line_no(self, value):
        """ Sets the current line number.
            """
        self._token_info['line_no'] = value

    @property
    def _token_chars(self):
        """ Gets the accumulated characters for current token.
            """
        return self._token_info['chars']

    @_token_chars.setter
    def _token_chars(self, value):
        """ Sets the accumulated characters for current token.
            """
        self._token_info['chars'] = value

    @property
    def _escaped(self):
        """ Escape character is at end of accumulated token
            character list.
            """

        chars = self._token_info['chars']
        count = len(chars)

        # prev char is escape, keep going
        if count and chars[count - 1] == self.ESCAPE:
            chars.pop()  # swallow escape char
            return True
        else:
            return False

    @property
    def filename(self):
        """ Returns filename for lexed file.
            """
        return self._filename

    @property
    def tokens(self):
        """ Returns lexed tokens.
            """
        for token in self._tokens:
            yield token
