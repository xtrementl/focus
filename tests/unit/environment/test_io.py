import os
import types

from focus_unittest import FocusTestCase
from focus.environment.io import IOStream


class TestIOStream(FocusTestCase):
    class Mock(object):
        def read(self):
            return '!!TESTING!! Hello World'

        def write(self, s):
            self.test__data = s

    def setUp(self):
        super(TestIOStream, self).setUp()
        self.io = IOStream(inputs=self.Mock(), outputs=self.Mock(),
                           errors=self.Mock())

    def tearDown(self):
        self.io = None
        super(TestIOStream, self).tearDown()

    def test__read(self):
        """ IOStream.read: reads data from input stream.
            """
        self.assertEqual(self.io.read(), '!!TESTING!! Hello World')

    def test__write(self):
        """ IOStream.write: writes data to output stream.
            """
        testval = 'TESTING...1.2.3!'
        self.io.write(testval, newline=False)
        self.assertEqual(self.io._output.test__data, testval)
        self.io.write(testval, newline=True)
        self.assertEqual(self.io._output.test__data, testval + os.linesep)

    def test__success(self):
        """ IOStream.success: writes success-colored data to output stream.
            """
        testval = 'TESTING...1.2.3!'
        color_testval = '{0}TESTING...1.2.3!{1}'.format(self.io.ESCAPE_GREEN,
                                                        self.io.ESCAPE_CLEAR)
        # colored versions
        self.io.set_colored(True)
        self.io.success(testval, newline=False)
        self.assertEqual(self.io._output.test__data, color_testval)
        self.io.success(testval, newline=True)
        self.assertEqual(self.io._output.test__data, color_testval +
                         os.linesep)

        # non-colored versions
        self.io.set_colored(False)
        self.io.success(testval, newline=False)
        self.assertEqual(self.io._output.test__data, testval)
        self.io.success(testval, newline=True)
        self.assertEqual(self.io._output.test__data, testval + os.linesep)

    def test__error(self):
        """ IOStream.error: writes error-colored data to error stream.
            """
        testval = 'TESTING...1.2.3!'
        color_testval = '{0}TESTING...1.2.3!{1}'.format(self.io.ESCAPE_RED,
                                                        self.io.ESCAPE_CLEAR)
        # colored versions
        self.io.set_colored(True)
        self.io.error(testval, newline=False)
        self.assertEqual(self.io._error.test__data, color_testval)
        self.io.error(testval, newline=True)
        self.assertEqual(self.io._error.test__data, color_testval + os.linesep)

        # non-colored versions
        self.io.set_colored(False)
        self.io.error(testval, newline=False)
        self.assertEqual(self.io._error.test__data, testval)
        self.io.error(testval, newline=True)
        self.assertEqual(self.io._error.test__data, testval + os.linesep)

    def test__set_colored(self):
        """ IOStream.set_colored: enables or disables coloring of output data.
            """
        self.io.set_colored(False)
        self.assertFalse(self.io._colored)
        self.io.set_colored(True)
        self.assertTrue(self.io._colored)

        self.io.set_colored(0)
        self.assertFalse(self.io._colored)
        self.io.set_colored(1)
        self.assertTrue(self.io._colored)

    def test__isatty(self):
        """ IOStream.isatty: is input stream a terminal.
            """
        # `Dummy` object doesn't have method.. should return False
        self.assertFalse(self.io.isatty)

        # patch in different `isatty` method versions to test return values
        self.io._input.isatty = types.MethodType(lambda self: True,
                                                 self.io._input)
        self.assertTrue(self.io.isatty)
        self.io._input.isatty = types.MethodType(lambda self: False,
                                                 self.io._input)
        self.assertFalse(self.io.isatty)
