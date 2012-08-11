""" This module provides a parser component for the `parser` package.
    """

import os
import re

from focus import common
from focus.parser.lexer import SettingLexer


class ParseError(Exception):
    """ Represents an error during parsing.
        """
    pass


class SettingParser(object):
    """ Simple parser that parses the tokens returned from the ``SettingLexer``
        class, which scans against configuration data.

        The following grammar describes the configuration file format::

            input     : container EOF
            container : NAME '{' (option | block)* '}'
            option    : NAME value ';'
            value     : TERM (',' TERM)*
            block     : NAME '{' option* '}'
            NAME      : ^[a-zA-Z_][a-zA-Z0-9_]*$
            TERM      : ^.+$

        where TERM has some additional constraints:
            a) Spaces, quotes, and token characters (i.e. {};,) must be escaped
               with the "\" char, unless they exist within a string.

               For example:
                    name John\ \"W\"\ Smith\,\ III;

               In the case of quotes, within strings they still have to be
               escaped if they match the surrounding quote char.

               For example, this:
                    name "John \"W\" Smith, III";

               versus, this:
                    name 'John "W" Smith, III';

            b) Strings can be either double or single-quoted; they just have to
               match. Within the string, the quote character can be escaped
               with the "\" char (i.e. \" for double quotes, \' for single).

               For example:
                    name "John \"W\" Smith, III";

               The escape char '\' may be used by itself or in double to
               represent one '\'.

               Example:
                    php_fug_namespace "$var = new A\\B\\FooBar();";

               Note, sometimes double escaping must be used to indicate a
               single escape char if adjacent to quote characters.

        Single-line comments are supported, starting with the '#' char. The
        comment continues until the end of the line.

        Also note, option names may be repeated, but blocks with the same name
        will be replaced with the last block taking precedence over the other
        blocks with the same name. Options within a single block may be
        repeated.

        The following is the layout of a supported configuration file::

            type_name {
                option_name value; # single-line comment
                option_name2 value, "other val", next\ val;
                option_name2 "value";
                option_name3 "value", "value 2";

                block_name {
                    option_name value;
                    option_name value, value2;
                    option_name2 value, value2;
                }

                block_name2 {
                    option_name value;
                    #...
                }

                option_name4 value;

                #...
            }

        Example Usage::

            >>> parser = SettingParser("task.cfg")
            >>> parser.header
            'task_config'
            >>> list(parser.options)
            [['duration', ['30']]]
            >>> list(parser.blocks)
            [['apps', [['block', ['spam-bin']]]]]

            >>> parser = SettingParser()
            >>> parser.read("task.cfg")
            True
            >>> parser.header
            'task_config'
            >>> list(parser.options)
            [['duration', ['30']]]
            >>> list(parser.blocks)
            [['apps', [['block', ['spam-bin']]]]]

            >>> parser = SettingParser()
            >>> with open("task.cfg", "r") as f:
            ...     parser.readstream(f)
            True
            >>> parser.header
            'task_config'
            >>> list(parser.options)
            [['duration', ['30']]]
            >>> list(parser.blocks)
            [['apps', [['block', ['spam-bin']]]]]

        The class also supports saving as a configuration file.

        Example Usage::

            >>> parser = SettingParser()
            >>> parser.add_option(None, "serv_days", "Mon", "Tues", "Wed",
            ...                   "Thurs", "Fri")
            >>> parser.add_block("servers")
            >>> parser.add_option("servers", "name", "John Smith")
            >>> parser.add_option("servers", "name", "Sally Sue")
            >>> parser.add_option("servers", "name", "Susie Q")
            >>> parser.add_option(None, "capacity", "75")
            >>> parser.write("lunch.cfg", "lunch")
            >>> open("lunch.cfg", "r").read()
            lunch {
                serv_days "Mon","Tues","Wed","Thurs","Fri";
                capacity "75";
                servers {
                    name "John Smith";
                    name "Sally Sue";
                    name "Susie Q";
                }
            }

        """
    RE_NAME = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*$')

    def __init__(self, filename=None):
        self._filename = None
        self._lexer = None
        self._ast = []
        self._block_map = {}

        self._reset()

        if filename:
            self.read(filename)

    def _reset(self):
        """ Rebuilds structure for AST and resets internal data.
            """

        self._filename = None
        self._block_map = {}
        self._ast = []
        self._ast.append(None)  # header
        self._ast.append([])    # options list
        self._ast.append([])    # block list

    def _get_token(self, regex=None):
        """ Consumes the next token in the token stream.

            `regex`
                Validate against the specified `re.compile()` regex instance.

            Returns token string.

            * Raises a ``ParseError`` exception if stream is empty or regex
              match fails.
            """

        item = self._lexer.get_token()

        if not item:
            raise ParseError(u'Unexpected end of file')
        else:
            line_no, token = item
            if regex and not regex.match(token):
                pattern = u"Unexpected format in token '{0}' on line {1}"
                token_val = common.from_utf8(token.strip())
                raise ParseError(pattern.format(token_val, line_no))

            return token

    def _lookahead_token(self, count=1):
        """ Peeks into the token stream up to the specified number of tokens
            without consuming any tokens from the stream.

            ``count``
                Look ahead in stream up to a maximum number of tokens.

            Returns string token or ``None``.
            """

        stack = []
        next_token = None

        # fetch the specified number of tokens ahead in stream
        while count > 0:
            item = self._lexer.get_token()
            if not item:
                break
            stack.append(item)
            count -= 1

        # store the latest token and push the tokens back on the
        # lexer stack so we don't consume them
        while stack:
            line_no, token = stack.pop()

            if not next_token:
                next_token = token
            self._lexer.push_token(line_no, token)

        return next_token

    def _expect_token(self, expected):
        """ Compares the next token in the stream to the specified token.

            `expected`
                Expected token string to match.

            * Raises a ``ParseError`` exception if token doesn't match
              `expected`.
            """

        item = self._lexer.get_token()

        if not item:
            raise ParseError(u'Unexpected end of file')

        else:
            line_no, token = item

        if token != expected:
            raise ParseError(u"Unexpected token '{0}', "
                             u"expecting '{1}' on line {2}"
                             .format(common.from_utf8(token.strip()), expected,
                                     line_no))

    def _expect_empty(self):
        """ Checks if the token stream is empty.

            * Raises a ``ParseError` exception if a token is found.
            """

        item = self._lexer.get_token()
        if item:
            line_no, token = item
            raise ParseError(u"Unexpected token '{0}' on line {1}"
                             .format(common.from_utf8(token.strip()), line_no))

    def _rule_container(self):
        """ Parses the production rule::
                container : NAME '{' (option | block)* '}' EOF

            Returns tuple (type_name, options_list, blocks_list).
            """

        type_name = self._get_token(self.RE_NAME)
        self._expect_token('{')

        # consume elements if available
        options = []
        blocks = []
        dupe_blocks = {}

        while self._lookahead_token() != '}':
            # is it a block?
            if self._lookahead_token(count=2) == '{':
                block = self._rule_block()
                name = block[0]

                # duplicate found, hold for replace
                if name in self._block_map:
                    dupe_blocks[name] = block
                else:
                    # update block index and add to block list
                    self._block_map[name] = len(blocks)
                    blocks.append(block)

            else:
                # otherwise, let's go with non-block option
                options.append(self._rule_option())

        # replace duplicate block definitions
        if dupe_blocks:
            for name, block in dupe_blocks.iteritems():
                block_idx = self._block_map[name]
                blocks[block_idx] = block

        self._expect_token('}')
        self._expect_empty()

        return [type_name, options, blocks]

    def _rule_option(self):
        """ Parses the production rule::
                option : NAME value ';'

            Returns list (name, value_list).
            """

        name = self._get_token(self.RE_NAME)
        value = self._rule_value()
        self._expect_token(';')
        return [name, value]

    def _rule_value(self):
        """ Parses the production rule::
                value : TERM (',' TERM)*

            Returns list of string terms.
            """

        terms = [self._get_token()]

        # consume additional terms if available
        while self._lookahead_token() == ',':
            self._get_token()  # chomp the comma
            terms.append(self._get_token())

        return terms

    def _rule_block(self):
        """ Parses the production rule::
                block : NAME '{' option* '}'

            Returns tuple (name, options_list).
            """

        name = self._get_token(self.RE_NAME)
        self._expect_token('{')

        # consume additional options if available
        options = []
        while self._lookahead_token() != '}':
            options.append(self._rule_option())

        self._expect_token('}')
        return [name, options]

    def _parse(self):
        """ Performs parsing process against token stream to generate the
            internal abstract syntax tree (AST) for general purpose use.

            * Raises a ``ParseError`` exception upon failure.
            """
        try:
            # parse token stream into abstract syntax tree (AST)
            self._ast = self._rule_container()

        except ParseError:
            raise

        except Exception as exc:
            raise ParseError(u'Unexpected error: {0}'.format(unicode(exc)))

    def read(self, filename):
        """ Reads the file specified and parses the token elements generated
            from tokenizing the input data.

            `filename`
                Filename to read.

            Returns boolean.
            """
        try:
            with open(filename, 'r') as _file:
                self.readstream(_file)
                self._filename = filename
            return True

        except IOError:
            self._reset()
            return False

    def readstream(self, stream):
        """ Reads the specified stream and parses the token elements generated
            from tokenizing the input data.

            `stream`
                ``File``-like object.

            Returns boolean.
            """

        self._reset()

        try:
            # tokenize input stream
            self._lexer = SettingLexer()
            self._lexer.readstream(stream)

            # parse tokens into AST
            self._parse()
            return True

        except IOError:
            self._reset()
            return False

    def write(self, filename, header=None):
        """ Writes the AST as a configuration file.

            `filename`
                Filename to save configuration file to.
            `header`
                Header string to use for the file.

            Returns boolean.
            """

        origfile = self._filename

        try:
            with open(filename, 'w') as _file:
                self.writestream(_file, header)
                self._filename = filename
            return True

        except IOError:
            self._filename = origfile
            return False

    def writestream(self, stream, header=None):
        """ Writes the AST as a configuration file to the File-like stream.

            `stream`
                ``File``-like object.
            `header`
                Header string to use for the stream.

            Returns boolean.

            * Raises a ``ValueError`` exception if `header` is invalid and
              a regular exception if no data is available to write to stream.
            """

        def serialize_values(values):
            """ Serializes list of values into the following format::
                    "value","value2","value3"
                """
            return ','.join('"{0}"'.format(v) for v in
                            (common.to_utf8(v).replace('\\', '\\\\')
                             .replace('"', '\\"') for v in values))

        if not self._ast:
            raise Exception(u'No available data to write to stream')

        header = header or self._ast[0]

        if not header:
            raise ValueError(u"Must provide a header")

        if not self.RE_NAME.match(header):
            raise ValueError(u"Invalid header")

        try:
            # write header, opening {
            stream.write('{0} {{{1}'.format(header, os.linesep))

            # write options
            for option, value_list in self.options:
                vals = serialize_values(value_list)
                stream.write('    {0} {1};{2}'.format(option, vals,
                                                      os.linesep))

            for block, option_list in self.blocks:
                # write block name, inner opening {
                stream.write('    {0} {{{1}'.format(block, os.linesep))

                # write options
                for option, value_list in option_list:
                    vals = serialize_values(value_list)
                    stream.write('        {0} {1};{2}'
                                 .format(option, vals, os.linesep))

                # write inner closing }
                stream.write('    }}{0}'.format(os.linesep))

            # write closing }
            stream.write('}}{0}'.format(os.linesep))

            # set the header
            self._ast[0] = header

            stream.flush()
            return True

        except IOError:
            return False

    def add_option(self, block, name, *values):
        """ Adds an option to the AST, either as a non-block option or for an
            existing block.

            `block`
                Block name. Set to ``None`` for non-block option.
            `name`
                Option name.
            `*values`
                String values for the option.

            * Raises a ``ValueError`` exception if `values` is empty, `name`
              is invalid, or `block` doesn't exist.
            """

        if not self.RE_NAME.match(name):
            raise ValueError(u"Invalid option name '{0}'"
                             .format(common.from_utf8(name)))

        if not values:
            raise ValueError(u"Must provide a value")
        else:
            values = list(values)

        if block:
            # block doesn't exist
            if not block in self._block_map:
                raise ValueError(u"Block '{0}' does not exist"
                                 .format(common.from_utf8(block)))

            # lookup block index and append
            block_idx = self._block_map[block]

            # 0: block name, 1: option_list
            self._ast[2][block_idx][1].append([name, values])

        else:
            # non-block option
            self._ast[1].append([name, values])

    def remove_option(self, block, name):
        """ Removes first matching option that exists from the AST.

            `block`
                Block name. Set to ``None`` for non-block option.
            `name`
                Option name to remove.

            * Raises a ``ValueError`` exception if `name` and/or `block`
              haven't been added.
            """

        if block:
            # block doesn't exist
            if not self._ast or not block in self._block_map:
                raise ValueError(u"Block '{0}' does not exist"
                                 .format(common.from_utf8(block)))

            # lookup block index and remove
            block_idx = self._block_map[block]

            for i, opt in enumerate(self._ast[2][block_idx][1]):
                if opt[0] == name:
                    item_idx = i
                    break
            else:
                raise ValueError(u"Option '{0}' does not exist"
                                 .format(common.from_utf8(name)))

            # pop off the block option
            options = self._ast[2][block_idx][1]
            options.pop(item_idx)

        else:
            if not self._ast:
                raise ValueError(u"Option '{0}' does not exist"
                                 .format(common.from_utf8(name)))

            # non-block option
            for i, opt in enumerate(self._ast[1]):
                if opt[0] == name:
                    item_idx = i
                    break
            else:
                raise ValueError(u"Option '{0}' does not exist"
                                 .format(common.from_utf8(name)))

            # pop off non-block option
            self._ast[1].pop(item_idx)

    def add_block(self, name):
        """ Adds a new block to the AST.

            `name`
                Block name.

            * Raises a ``ValueError`` exception if `name` is invalid or
              an existing block name matches value provided for `name`.
            """

        if not self.RE_NAME.match(name):
            raise ValueError(u"Invalid block name '{0}'"
                             .format(common.from_utf8(name)))

        if name in self._block_map:
            raise ValueError(u"Block '{0}' already exists"
                             .format(common.from_utf8(name)))

        # add new block and index mapping
        self._block_map[name] = len(self._ast[2])  # must come first
        option_list = []
        block = [name, option_list]
        self._ast[2].append(block)

    def remove_block(self, name):
        """ Removes an existing block from the AST.

            `name`
                Block name.

            * Raises a ``ValueError`` exception if `name` hasn't been added.
            """

        if not self._ast or not name in self._block_map:
            raise ValueError(u"Block '{0}' does not exist"
                             .format(common.from_utf8(name)))

        block_idx = self._block_map[name]

        # remove block
        self._ast[2].pop(block_idx)
        del self._block_map[name]

    @property
    def filename(self):
        """ Returns filename for parsed file.
            """
        return self._filename

    @property
    def header(self):
        """ Returns header available in parsed AST.
            """
        if not self._ast:
            return None
        else:
            return self._ast[0]

    @property
    def options(self):
        """ Returns generator of options available in parsed AST.
            """
        if self._ast:
            for option in self._ast[1]:
                yield option

    @property
    def blocks(self):
        """ Returns generator of blocks available in parsed AST.
            """
        if self._ast:
            for block in self._ast[2]:
                yield block
