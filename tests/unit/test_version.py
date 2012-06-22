from focus_unittest import FocusTestCase
from focus.version import __version_info__, compare_version


def _mkver(op, pos=0, inc=0):
    v = list(__version_info__)

    if pos == 0:
        pos = len(v) - 1

    while pos >= 0:
        v[pos] += inc
        if v[pos] < 0:
            v[pos] = 0
        pos -= 1

    return op + '.'.join(str(x) for x in v)


class TestVersion(FocusTestCase):
    def setUp(self):
        super(TestVersion, self).setUp()
        self.version = __version_info__

    def tearDown(self):
        self.version = None
        super(TestVersion, self).tearDown()

    def testCorrectVersion(self):
        """ version.compare_version: correct version defined.
            """
        self.assertEqual(self.version, (0, 1, 0))

    def testEqual__compare_version(self):
        """ version.compare_version: equal to's.
            """
        for i in range(len(self.version)):
            # earlier versions
            self.assertFalse(compare_version(_mkver('==', i, -1)))

            # later versions
            self.assertFalse(compare_version(_mkver('==', i, 1)))

        # zeros
        self.assertFalse(compare_version('==0.0'))
        self.assertFalse(compare_version('==0.0.0'))

        self.assertTrue(compare_version(_mkver('==')))

    def testLessThan__compare_version(self):
        """ version.compare_version: less thans.
            """
        for i in range(len(self.version)):
            # earlier versions
            self.assertFalse(compare_version(_mkver('<', i, -1)))

            # later versions
            self.assertTrue(compare_version(_mkver('<', i, 1)))

        # zeros
        self.assertFalse(compare_version('<0.0'))
        self.assertFalse(compare_version('<0.0.0'))

        self.assertFalse(compare_version(_mkver('<')))

    def testLessThanEqual__compare_version(self):
        """ version.compare_version: less than or equal to's.
            """
        for i in range(len(self.version)):
            # earlier versions
            self.assertFalse(compare_version(_mkver('<=', i, -1)))

            # later versions
            self.assertTrue(compare_version(_mkver('<=', i, 1)))

        # zeros
        self.assertFalse(compare_version('<=0.0'))
        self.assertFalse(compare_version('<=0.0.0'))

        self.assertTrue(compare_version(_mkver('<=')))

    def testGreaterThan__compare_version(self):
        """ version.compare_version: greater thans.
            """
        for i in range(len(self.version)):
            # lower versions
            self.assertTrue(compare_version(_mkver('>', i, -1)))

            # higher versions
            self.assertFalse(compare_version(_mkver('>', i, 1)))

        # zeros
        self.assertTrue(compare_version('>0.0'))
        self.assertTrue(compare_version('>0.0.0'))

        self.assertFalse(compare_version(_mkver('>')))

    def testGreaterThanEqual__compare_version(self):
        """ version.compare_version: greater than or equal to's.
            """
        for i in range(len(self.version)):
            # lower versions
            self.assertTrue(compare_version(_mkver('>=', i, -1)))

            # higher versions
            self.assertFalse(compare_version(_mkver('>=', i, 1)))

        # zeros
        self.assertTrue(compare_version('>=0.0'))
        self.assertTrue(compare_version('>=0.0.0'))

        self.assertTrue(compare_version(_mkver('>=')))

    def testInvalidFormat__compare_version(self):
        """ version.compare_version: invalid values.
            """
        for v in ('<-1', '<-1.2.0', '>-5.0', '<JjN$#$&88', '<=AKJ#*jdf',
                  '==AB*#*U#$J' '>AKJ#*jdf', '>=j#$OF*U$%', None, tuple(),
                  list(), object(), dict(), set()):

            self.assertFalse(compare_version(v))
