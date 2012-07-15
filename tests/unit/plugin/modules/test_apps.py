import os
import time
import shutil
import psutil
import subprocess

from focus.plugin.modules import apps as plugins
from focus_unittest import FocusTestCase, MockTask


class CloseAppCase(FocusTestCase):
    def setUp(self):
        super(CloseAppCase, self).setUp()
        self.setup_dir()

    def _kill_app(self, method, process_count):
        """ Confirms that a number of test apps are terminated after the
            provided method is executed.

            `method`
                Callable to execute when testing app terminate functionality.
                This method will be passed the filename for the test app binary
                that will be launched to test against.
            `process_count`
                Number of test apps to launch that are supposed to be killed.

            Returns ``True`` if all launched apps were successfully terminated.
            """

        # range check
        if process_count > 20:
            process_count = 20
        if process_count < 1:
            process_count = 1

        # make a copy of 'sh' shell binary and alter it so it has a unique
        # checksum for this binary, so we don't kill other running instances of
        # bin/sh
        bin_file = self.make_file()
        shutil.copyfile('/bin/sh', bin_file)

        # change the checksum of the binary
        open(bin_file, 'a+b', 0).write('A' * 100)
        os.chmod(bin_file, 0700)  # set exec.. silly macosx

        # launch copied shell binary in background
        processes = {}
        for i in range(process_count):
            proc = subprocess.Popen([bin_file, '-c',
                                     'while true; do sleep 1; done'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    stdin=subprocess.PIPE)
            processes[proc.pid] = proc

        # call provided method
        method(bin_file)

        i = 0
        while i < 1500:
            i += 1

            try:
                # wait for the processes to die; reclaim process entries
                pid, status = os.waitpid(-1, os.P_NOWAIT)
                time.sleep(0.05)
            except OSError:
                break

            if pid in processes:
                del processes[pid]

        fail = False
        if processes:
            fail = True

            # kill what's leftover
            for pid, proc in processes.iteritems():
                try:
                    proc.terminate()
                    proc.wait()
                except OSError:
                    pass

        return (not fail)


class TestAppRun(FocusTestCase):
    def setUp(self):
        super(TestAppRun, self).setUp()
        self.setup_dir()
        self.task = MockTask()
        self.plugin = plugins.AppRun()

    def tearDown(self):
        self.plugin = None
        self.task = None
        super(TestAppRun, self).tearDown()

    def testPathKeys__parse_option(self):
        """ AppRun.parse_option: check if option names set correct path keys.
            """
        self.plugin.parse_option('run', 'apps', 'cat')
        self.assertIn('start', self.plugin.paths)
        self.assertEqual(self.plugin.paths['start'], set(['/bin/cat']))

        self.plugin.parse_option('end_run', 'apps', 'cp')
        self.assertIn('end', self.plugin.paths)
        self.assertEqual(self.plugin.paths['end'], set(['/bin/cp']))

        self.plugin.parse_option('timer_run', 'apps', 'cat')
        self.assertIn('timer', self.plugin.paths)
        self.assertEqual(self.plugin.paths['timer'], set(['/bin/cat']))

    def testDedupeOptionValue__parse_option(self):
        """ AppRun.parse_option: duplicate values for options are
            removed.
            """
        self.plugin.parse_option('run', 'apps', 'cat')
        self.plugin.parse_option('run', 'apps', 'cat')
        self.assertEqual(self.plugin.paths, dict(start=set(['/bin/cat'])))

    def testMultiValueOption__parse_option(self):
        """ AppRun.parse_option: options support multiple values.
            """
        self.plugin.parse_option('run', 'apps', 'cat', 'chmod')
        self.assertEqual(self.plugin.paths,
            dict(start=set(['/bin/cat', '/bin/chmod'])))

    def testOptionsSupportArguments__parse_option(self):
        """ AppRun.parse_option: options support arguments for values.
            """
        self.plugin.parse_option('run', 'apps', 'cp notexist nowhere')
        self.assertEqual(self.plugin.paths,
            dict(start=set(['/bin/cp notexist nowhere'])))

    def testOptionValue_CommandsExist__parse_option(self):
        """ AppRun.parse_option: extracts option values are existing commands.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('run', 'apps', 'non-existent-cmd')
        with self.assertRaises(ValueError):
            self.plugin.parse_option('run', 'apps', '/bin/non-existent-cmd')

    def test__on_taskstart(self):
        """ AppRun.on_taskstart: configured apps are launched.
            """

        # make a copy of 'sh' shell binary so we have something unique that we
        # can have plugin launch and check for accurately
        bin_file = self.make_file()
        self.plugin.paths['start'] = set([bin_file])
        shutil.copyfile('/bin/sh', bin_file)
        os.chmod(bin_file, 0700)  # set exec.. silly macosx

        self.plugin.on_taskstart(self.task)

        found = False
        uid = os.getuid()

        # check user's process list for app
        for p in psutil.process_iter():
            try:
                if p.uids.real == uid:
                    try:
                        path = p.exe
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        path = None

                    if path == bin_file:
                        found = True

                        # terminate the process and wait till exit
                        p.terminate()
                        p.wait()
                        break

            except Exception:
                if found:
                    break

        self.assertTrue(found)


class TestAppClose(CloseAppCase):
    def setUp(self):
        super(TestAppClose, self).setUp()
        self.task = MockTask()
        self.plugin = plugins.AppClose()

    def tearDown(self):
        self.plugin = None
        self.task = None
        super(TestAppClose, self).tearDown()

    def testPathKeys__parse_option(self):
        """ AppClose.parse_option: check if option names set correct path keys.
            """
        self.plugin.parse_option('close', 'apps', 'cat')
        self.assertIn('start', self.plugin.paths)
        self.assertEqual(self.plugin.paths['start'], set(['/bin/cat']))

        self.plugin.parse_option('end_close', 'apps', 'cp')
        self.assertIn('end', self.plugin.paths)
        self.assertEqual(self.plugin.paths['end'], set(['/bin/cp']))

        self.plugin.parse_option('timer_close', 'apps', 'cat')
        self.assertIn('timer', self.plugin.paths)
        self.assertEqual(self.plugin.paths['timer'], set(['/bin/cat']))

    def testDedupeOptionValue__parse_option(self):
        """ AppClose.parse_option: duplicate values for options are
            removed.
            """
        self.plugin.parse_option('close', 'apps', 'cat')
        self.plugin.parse_option('close', 'apps', 'cat')
        self.assertEqual(self.plugin.paths, dict(start=set(['/bin/cat'])))

    def testMultiValueOption__parse_option(self):
        """ AppClose.parse_option: options support multiple values.
            """
        self.plugin.parse_option('close', 'apps', 'cat', 'chmod')
        self.assertEqual(self.plugin.paths,
            dict(start=set(['/bin/cat', '/bin/chmod'])))

    def testOptionsSpacesAsName__parse_option(self):
        """ AppClose.parse_option: program arguments are treated as
            part of the program name (e.g. google chrome => "google chrome",
            instead of just "google".
            """
        # no "cp notexist nowhere" binary in search path
        with self.assertRaises(ValueError):
            self.plugin.parse_option('close', 'apps', 'cp notexist nowhere')
        self.plugin.parse_option('close', 'apps', 'cp')
        self.assertEqual(self.plugin.paths, dict(start=set(['/bin/cp'])))

    def testOptionValue_CommandsExist__parse_option(self):
        """ AppClose.parse_option: option values are existing commands.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('close', 'apps', 'non-existent-cmd')
        with self.assertRaises(ValueError):
            self.plugin.parse_option('close', 'apps', '/bin/non-existent-cmd')

    def test__on_taskstart(self):
        """ AppClose.on_taskstart: configured running apps are closed.
            """
        def _method(path):
            if not 'start' in self.plugin.paths:
                self.plugin.paths['start'] = set()
            self.plugin.paths['start'].add(path)
            self.plugin.on_taskstart(self.task)
        self.assertTrue(self._kill_app(_method, process_count=3))


class TestAppBlock(CloseAppCase):
    def setUp(self):
        super(TestAppBlock, self).setUp()
        self.task = MockTask()
        self.plugin = plugins.AppBlock()

    def tearDown(self):
        self.plugin = None
        self.task = None
        super(TestAppBlock, self).tearDown()

    def testDedupeOptionValue__parse_option(self):
        """ AppBlock.parse_option: duplicate values for options are
            removed.
            """
        self.plugin.parse_option('block', 'apps', 'cat')
        self.plugin.parse_option('block', 'apps', 'cat')
        self.assertEqual(self.plugin.paths, dict(block=set(['/bin/cat'])))

    def testMultiValueOption__parse_option(self):
        """ AppBlock.parse_option: options support multiple values.
            """
        self.plugin.parse_option('block', 'apps', 'cat', 'chmod')
        self.assertEqual(self.plugin.paths,
            dict(block=set(['/bin/cat', '/bin/chmod'])))

    def testOptionsSpacesAsName__parse_option(self):
        """ AppBlock.parse_option: program arguments are treated as
            part of the program name (e.g. google chrome => "google chrome",
            instead of just "google".
            """
        # no "cp notexist nowhere" binary in search path
        with self.assertRaises(ValueError):
            self.plugin.parse_option('block', 'apps', 'cp notexist nowhere')
        self.plugin.parse_option('block', 'apps', 'cp')
        self.assertEqual(self.plugin.paths, dict(block=set(['/bin/cp'])))

    def testOptionValue_CommandsExist__parse_option(self):
        """ AppBlock.parse_option: option values are existing commands.
            """
        with self.assertRaises(ValueError):
            self.plugin.parse_option('block', 'apps', 'non-existent-cmd')
        with self.assertRaises(ValueError):
            self.plugin.parse_option('block', 'apps', '/bin/non-existent-cmd')

    def test__on_taskrun(self):
        """ AppBlock.on_taskrun: configured running apps are closed.
            """
        def _method(path):
            if not 'block' in self.plugin.paths:
                self.plugin.paths['block'] = set()
            self.plugin.paths['block'].add(path)
            self.plugin.on_taskrun(self.task)
        self.assertTrue(self._kill_app(_method, process_count=3))
