""" This package provides a lexical scanner and parser class to parse
    configuration files used within the system.

    It provides interfaces to parse, query, and write configuration files.
    """

from focus import common
from focus.parser.lexer import SettingLexer
from focus.parser.parser import SettingParser, ParseError


__all__ = ('parse_config', 'ParseError', 'SettingLexer', 'SettingParser')


def parse_config(filename, header):
    """ Parses the provided filename and returns ``SettingParser`` if the
        parsing was successful and header matches the header defined in the
        file.

        Returns ``SettingParser`` instance.

        * Raises a ``ParseError`` exception if header doesn't match or parsing
          fails.
        """

    parser = SettingParser(filename)
    if parser.header != header:
        header_value = parser.header or ''
        raise ParseError(u"Unexpected header '{0}', expecting '{1}'"
                         .format(common.from_utf8(header_value), header))

    return parser
