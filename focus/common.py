""" This module provides generic utilities that are shared between any module
    in the system.
    """

import os
import sys
import shlex
import subprocess

__all__ = ('IS_MACOSX', 'readfile', 'writefile', 'safe_remove_file', 'which',
           'extract_app_paths', 'shell_process', 'to_utf8', 'from_utf8')


# platform is mac osx
IS_MACOSX = sys.platform.lower().startswith('darwin')


def readfile(filename, binary=False):
    """ Reads the contents of the specified file.

        `filename`
            Filename to read.
        `binary`
            Set to ``True`` to indicate a binary file.

        Returns string or ``None``.
        """

    if not os.path.isfile(filename):
        return None

    try:
        flags = 'r' if not binary else 'rb'
        with open(filename, flags) as _file:
            return _file.read()

    except (OSError, IOError):
        return None


def writefile(filename, data, binary=False):
    """ Write the provided data to the file.

        `filename`
            Filename to write.
        `data`
            Data buffer to write.
        `binary`
            Set to ``True`` to indicate a binary file.

        Returns boolean.
        """
    try:
        flags = 'w' if not binary else 'wb'
        with open(filename, flags) as _file:
            _file.write(data)
            _file.flush()
            return True

    except (OSError, IOError):
        return False


def safe_remove_file(filename):
    """ Removes the specified filename without raising exceptions.
        """
    try:
        os.remove(filename)
        return True

    except OSError:
        return False


def which(name):
    """ Returns the full path to executable in path matching provided name.

        `name`
            String value.

        Returns string or ``None``.
        """

    # we were given a filename, return it if it's executable
    if os.path.dirname(name) != '':
        if not os.path.isdir(name) and os.access(name, os.X_OK):
            return name
        else:
            return None

    # fetch PATH env var and split
    path_val = os.environ.get('PATH', None) or os.defpath

    # return the first match in the paths
    for path in path_val.split(os.pathsep):
        filename = os.path.join(path, name)

        if os.access(filename, os.X_OK):
            return filename

    return None


def extract_app_paths(values, app_should_exist=True):
    """ Extracts application paths from the values provided.

        `values`
            List of strings to extract paths from.
        `app_should_exist`
            Set to ``True`` to check that application file exists.

        Returns list of strings.

        * Raises ``ValueError`` exception if value extraction fails.
        """

    def _osx_app_path(name):
        """ Attempts to find the full application path for the name specified.

            `name`
                Application name.

            Returns string or ``None``.
            """

        # we use find because it is faster to traverse the
        # hierachy for app dir.
        cmd = ('find /Applications -type d '
               '-iname "{0}.app" -maxdepth 4'.format(name))

        data = shell_process(cmd)
        if not data is None:
            lines = str(data).split('\n')

            if lines:
                bundle_dir = lines[0]
                path = os.path.join(bundle_dir, 'Contents', 'MacOS', name)

                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path

        return None

    paths = set()

    for value in values:
        # split path into relevant tokens
        parts = list(shlex.split(value))

        # program name
        name = parts[0]

        # just the name, search bin paths
        if os.path.dirname(name) == '':
            path = which(name)

            if not path:
                # MacOS X, maybe it's an application name; let's try to build
                # default application binary path
                errmsg = u'"{0}" command does not exist'.format(name)

                if IS_MACOSX:
                    path = _osx_app_path(name)
                    if not path:
                        raise ValueError(errmsg)
                else:
                    raise ValueError(errmsg)  # no luck

        else:
            # relative to current working dir or full path
            path = os.path.realpath(name)

            if app_should_exist:
                # should be a file or link and be executable
                if os.path.isdir(path) or not os.access(path, os.X_OK):
                    errmsg = u'"{0}" is not an executable file'.format(name)
                    raise ValueError(errmsg)

        # update program path
        parts[0] = path

        # quote params with spaces in value
        parts[:] = ['"{0}"'.format(p.replace('"', '\\"'))
                    if ' ' in p else p for p in parts]

        # add flattened path
        paths.add(' '.join(parts))

    return list(paths)


def shell_process(command, input_data=None, background=False, exitcode=False):
    """ Shells a process with the given shell command.

        `command`
            Shell command to spawn.
        `input_data`
            String to pipe to process as input.
        `background`
            Set to ``True`` to fork process into background.
            NOTE: This exits immediately with no result returned.
        `exitcode`
            Set to ``True`` to also return process exit status code.

        if `exitcode` is ``False``, then this returns output string from
        process or ``None`` if it failed.

        otherwise, this returns a tuple with output string from process or
        ``None`` if it failed and the exit status code.

            Example::
                (``None``, 1) <-- failed
                ('Some data', 0) <-- success
        """

    data = None

    try:
        # kick off the process
        kwargs = {
            'shell': isinstance(command, basestring),
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE
        }
        if not input_data is None:
            kwargs['stdin'] = subprocess.PIPE
        proc = subprocess.Popen(command, **kwargs)

        # background exits without checking anything
        if not background:
            output, _ = proc.communicate(input_data)
            retcode = proc.returncode

            if retcode == 0:
                data = str(output).rstrip()
        else:
            retcode = None

            if input_data:
                raise TypeError(u'Backgrounded does not support input data.')

    except OSError as exc:
        retcode = -exc.errno

    if exitcode:
        return data, retcode

    else:
        return data


def to_utf8(buf, errors='replace'):
    """ Encodes a string into a UTF-8 compatible, ASCII string.

        `buf`
            string or unicode to convert.

        Returns string.

        * Raises a ``UnicodeEncodeError`` exception if encoding failed and
          `errors` isn't set to 'replace'.
        """

    if isinstance(buf, unicode):
        return buf.encode('utf-8', errors)

    else:
        return buf


def from_utf8(buf, errors='replace'):
    """ Decodes a UTF-8 compatible, ASCII string into a unicode object.

        `buf`
            string or unicode string to convert.

        Returns unicode` string.

        * Raises a ``UnicodeDecodeError`` exception if encoding failed and
          `errors` isn't set to 'replace'.
        """

    if isinstance(buf, unicode):
        return buf

    else:
        return unicode(buf, 'utf-8', errors)
