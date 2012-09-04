""" This module provides the project version info and comparison utility.
    """

__version_info__ = (0, 1, 1)
__version__ = '.'.join(str(x) for x in __version_info__)


def compare_version(value):
    """ Determines if the provided version value compares with program version.

        `value`
            Version comparison string (e.g. ==1.0, <=1.0, >1.1)
                Supported operators:
                    <, <=, ==, >, >=
        """

    # extract parts from value
    import re
    res = re.match(r'(<|<=|==|>|>=)(\d{1,2}\.\d{1,2}(\.\d{1,2})?)$',
                   str(value).strip())
    if not res:
        return False
    operator, value, _ = res.groups()

    # break into pieces
    value = tuple(int(x) for x in str(value).split('.'))
    if len(value) < 3:
        value += (0,)

    version = __version_info__

    if operator in ('<', '<='):
        if version < value:
            return True

        if operator != '<=':
            return False

    elif operator in ('>=', '>'):
        if version > value:
            return True

        if operator != '>=':
            return False

    return value == version
