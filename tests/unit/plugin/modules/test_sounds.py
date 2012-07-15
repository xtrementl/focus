from focus_unittest import FocusTestCase
from focus.plugin.modules import sounds as plugins


class TestPlaySound(FocusTestCase):
    def setUp(self):
        super(TestPlaySound, self).setUp()
        self.plugin = plugins.PlaySound()

    def tearDown(self):
        self.plugin = None
        super(TestPlaySound, self).tearDown()

    def testNonExist_Play__parse_option(self):
        """ PlaySound.parse_option: invalid file provided for sounds.play
            option.
            """
        for opt in ('play', 'end_play', 'timer_play'):
            with self.assertRaises(ValueError):
                self.plugin.parse_option(opt, 'sounds', 'non-exist-file')
