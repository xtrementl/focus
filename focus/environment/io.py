""" This module provides the stream encapsulation class for the runtime
    environment.
    """

import os
import errno


class IOStream(object):
    """ Basic abstraction interface for IO streams.

    Example Usage::

        >>> io = IOStream()
        >>> data = io.read()  # read from input stream
        >>> io.write(data)  # mirror input
        >>> io.success(u"Successful response")
        >>> io.error(u"Error response")

        >>> io = IOStream(error=IOStream.NullDevice())
        >>> io.error(u"This goes into the void.")
        """

    class NullDevice(object):
        """ Dummy device that reads nothing and writes nowhere, like /dev/null
            """
        def read(self):
            """ Return empty string for standard input stream data.
                """
            return ''

        def readline(self):
            """ Return empty string for standard input stream line data.
                """
            return ''

        def write(self, buf):
            """ Write nothing to output stream.
                """
            pass

        def flush(self):
            """ Flushes nothing.
                """
            pass

        def isatty(self):
            """ Not a terminal.
                """
            return False

    # escape codes
    ESCAPE_RED = '\033[1;31m'
    ESCAPE_GREEN = '\033[1;32m'
    ESCAPE_CLEAR = '\033[0m'

    def __init__(self, auto_colored=True, inputs=None, outputs=None,
                 errors=None):
        """ Initializes class.

            ``auto_colored``
                Automatically detect if output and error streams support
                colorized escape codes.

            Additional keyword arguments:

                `inputs`
                    :Default: ``NullDevice``

                    Input stream (``File``-like object).

                `outputs`
                    :Default: ``NullDevice``

                    Output stream (``File``-like object).

                `errors`
                    :Default: ``NullDevice``

                    Error output stream (``File``-like object).
            """

        self._input = inputs or self.NullDevice()
        self._output = outputs or self.NullDevice()
        self._error = errors or self.NullDevice()

        # set colored if input stream is a terminal
        self._colored = bool(auto_colored and self.isatty)

    def read(self):
        """ Returns string from input stream.
            """
        return self._input.read().rstrip(os.linesep)

    def prompt(self, prompt_msg=None, newline=False):
        """ Writes prompt message to output stream and
            reads line from standard input stream.

            `prompt_msg`
                Message to write.
            `newline`
                Append newline character to prompt message before writing.

            Return string.
            """

        if prompt_msg is not None:
            self.write(prompt_msg, newline)

        return self._input.readline().rstrip(os.linesep)

    def write(self, buf, newline=True):
        """ Writes buffer to output stream.

            `buf`
                Data buffer to write.
            `newline`
                Append newline character to buffer before writing.
            """

        buf = buf or ''

        if newline:
            buf += os.linesep

        try:
            self._output.write(buf)

            if hasattr(self._output, 'flush'):
                self._output.flush()

        except IOError as exc:
            if exc.errno != errno.EPIPE:  # silence EPIPE errors
                raise

    def success(self, buf, newline=True):
        """ Same as `write`, but adds success coloring if enabled.

            `buf`
                Data buffer to write.
            `newline`
                Append newline character to buffer before writing.
            """

        if self._colored:
            buf = self.ESCAPE_GREEN + buf + self.ESCAPE_CLEAR

        self.write(buf, newline)

    def error(self, buf, newline=True):
        """ Similar to `write`, except it writes buffer to error stream.
            If coloring enabled, adds error coloring.

            `buf`
                Data buffer to write.
            `newline`
                Append newline character to buffer before writing.
            """

        buf = buf or ''

        if self._colored:
            buf = self.ESCAPE_RED + buf + self.ESCAPE_CLEAR
        if newline:
            buf += os.linesep

        try:
            self._error.write(buf)

            if hasattr(self._error, 'flush'):
                self._error.flush()

        except IOError as exc:
            if exc.errno != errno.EPIPE:  # silence EPIPE errors
                raise

    def set_colored(self, enable):
        """ Enables or disables coloring for this stream.
            """
        self._colored = bool(enable)

    @property
    def isatty(self):
        """ Determines this stream a terminal.
            """

        if hasattr(self._input, 'isatty'):
            return self._input.isatty()
        else:
            return False
