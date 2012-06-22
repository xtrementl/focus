""" This module provides generic utilities that are shared between any module
    in the system.
    """

import os

from focus import common
from focus_unittest import FocusTestCase


class TestCommon(FocusTestCase):
    def setUp(self):
        super(TestCommon, self).setUp()
        self.setup_dir()

    def testExistFile__readfile(self):
        """ common.readfile: returns contents for existing files.
            """
        # text file
        data = 'this is a test' + os.linesep
        filename = self.make_file(data)
        self.assertEqual(common.readfile(filename, binary=False), data)

        # binary file
        data = '\x00\x12\x34\x56\x78'
        filename = self.make_file(data)
        self.assertEqual(common.readfile(filename, binary=True), data)

    def testNotExistFile__readfile(self):
        """ common.readfile: returns ``None`` for non-existent files.
            """
        filename = self.make_file()
        self.clean_paths(filename)
        self.assertIsNone(common.readfile(filename))

    def test__writefile(self):
        """ common.writefile: writes contents to file.
            """
        # text file
        filename = self.make_file()
        data = 'this is a test' + os.linesep
        self.assertTrue(common.writefile(filename, data, binary=False))
        self.assertEqual(open(filename, 'r').read(), data)

        # binary file
        filename = self.make_file()
        data = '\x00\x12\x34\x56\x78'
        self.assertTrue(common.writefile(filename, data, binary=True))
        self.assertEqual(open(filename, 'rb').read(), data)

    def testExistFile__safe_remove_file(self):
        """ common.safe_remove_file: removes existing file.
            """
        filename = self.make_file()
        self.assertTrue(common.safe_remove_file(filename))

    def testNotExistFile__safe_remove_file(self):
        """ common.safe_remove_file: doesn't raise when trying to remove a
            non-existent file.
            """
        filename = self.make_file()
        self.clean_paths(filename)
        self.assertFalse(common.safe_remove_file(filename))

    def testExistCommand__which(self):
        """ common.which: returns full path for existing commands.
            """
        self.assertEqual(common.which('cat'), '/bin/cat')
        self.assertEqual(common.which('ls'), '/bin/ls')
        self.assertEqual(common.which('rm'), '/bin/rm')

    def testNotExistCommand__which(self):
        """ common.which: returns ``None`` for non-existent commands.
            """
        self.assertIsNone(common.which('this-is-fake-command'))

    def testReturnPath__which(self):
        """ common.which: returns same value if path is given.
            """
        self.assertEqual(common.which('/bin/cat'), '/bin/cat')

    def testReturnPathNonExecOrDir__which(self):
        """ common.which: returns ``None`` if value is a path and it's a
            directory or non-executable file.
            """
        self.assertIsNone(common.which('/bin'))
        self.assertIsNone(common.which('/etc/hosts'))

    def testDedupeValue__extract_app_paths(self):
        """ common.extract_app_paths: removes duplicate values.
            """
        self.assertEqual(common.extract_app_paths(['cat', 'cat']),
                         ['/bin/cat'])

    def testMultiValue__extract_app_paths(self):
        """ common.extract_app_paths: supports multiple values.
            """
        vals = common.extract_app_paths(['cat', 'chmod'])
        expected = ['/bin/cat', '/bin/chmod']

        for val in vals:
            self.assertIn(val, expected)

    def testSupportArguments__extract_app_paths(self):
        """ common.extract_app_paths: supports arguments for values.
            """
        self.assertEqual(common.extract_app_paths(['cp notexist nowhere']),
                         ['/bin/cp notexist nowhere'])

    def testCommandsExist__extract_app_paths(self):
        """ common.extract_app_paths: extracts values that are existing
            commands.
            """
        with self.assertRaises(ValueError):
            common.extract_app_paths(['non-existent-cmd'])
        with self.assertRaises(ValueError):
            common.extract_app_paths(['/bin/non-existent-cmd'])
    
    def testExistCommand__shell_process(self):
        """ common.shell_process: works if command doesn't exist.
            """
        # test foregrounded
        self.assertIsNotNone(common.shell_process('ls'))
        res = common.shell_process('ls', exitcode=True)
        self.assertIsNotNone(res[0])
        self.assertEqual(res[1], 0)

        # test backgrounded, returns immediately with None
        self.assertIsNone(common.shell_process('ls', background=True))
        res = common.shell_process('ls', exitcode=True, background=True)
        self.assertIsNone(res[0])
        self.assertIsNone(res[1])

    def testExistCommandInputData__shell_process(self):
        """ common.shell_process: passes input data to process and supports
            shell redirection.
            """
        # test foregrounded
        self.assertEqual(common.shell_process('cat -', input_data='monkeys'),
                         'monkeys')

        res = common.shell_process('cat -', exitcode=True,
                                   input_data='monkeys')
        self.assertEqual(res[0], 'monkeys')
        self.assertEqual(res[1], 0)

        # backgrounded doesn't support passing `input`
        with self.assertRaises(TypeError):
            common.shell_process('ls', background=True, input_data='monkeys')
        with self.assertRaises(TypeError):
            common.shell_process('ls', exitcode=True, background=True,
                input_data='monkeys')

    def testNotExistCommand__shell_process(self):
        """ common.shell_process: fails if command doesn't exist.
            """
        # test foregrounded
        self.assertIsNone(common.shell_process('llama-llama'))
        res = common.shell_process('llama-llama', exitcode=True)
        self.assertIsNone(res[0])
        self.assertEqual(res[1], 127)  # shell exit code, command not found

        # test backgrounded, returns immediately with None
        self.assertIsNone(common.shell_process('llama-llama', background=True))
        res = common.shell_process('llama-llama', exitcode=True,
                                   background=True)
        self.assertIsNone(res[0])
        self.assertIsNone(res[1])

    def testStr__to_utf8(self):
        """ common.to_utf8: returns same value if already str:
            """
        self.assertIsInstance(common.to_utf8('hey'), str)
        self.assertEqual(common.to_utf8('hey'), 'hey')

    def testUnicode__to_utf8(self):
        """ common.to_utf8: properly encodes ``unicode`` string to ``str``
            type.
            """
        # strings of urdu chars
        u = (u'\u06be\u06d2\u062a\u06a9\u0644\u06cc\u0641\u0646'
             u'\u06c1\u06cc\u06ba\u06c1\u0648\u062a\u06cc')
        s = ('\xda\xbe\xdb\x92\xd8\xaa\xda\xa9\xd9\x84\xdb'
             '\x8c\xd9\x81\xd9\x86\xdb\x81\xdb\x8c\xda\xba'
             '\xdb\x81\xd9\x88\xd8\xaa\xdb\x8c')
        self.assertIsInstance(common.to_utf8(u), str)
        self.assertEqual(common.to_utf8(u), s)

    def testUnicode__from_utf8(self):
        """ common.from_utf8: returns same value if already unicode.
            """
        self.assertIsInstance(common.from_utf8(u'hey'), unicode)
        self.assertEqual(common.from_utf8(u'hey'), u'hey')

    def testStr__from_utf8(self):
        """ common.from_utf8: properly encodes ``str`` string to ``unicode``
            type.
            """
        # strings of urdu chars
        u = (u'\u06be\u06d2\u062a\u06a9\u0644\u06cc\u0641\u0646'
             u'\u06c1\u06cc\u06ba\u06c1\u0648\u062a\u06cc')
        s = ('\xda\xbe\xdb\x92\xd8\xaa\xda\xa9\xd9\x84\xdb'
             '\x8c\xd9\x81\xd9\x86\xdb\x81\xdb\x8c\xda\xba'
             '\xdb\x81\xd9\x88\xd8\xaa\xdb\x8c')
        self.assertIsInstance(common.from_utf8(s), unicode)
        self.assertEqual(common.from_utf8(s), u)
