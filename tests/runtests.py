import os
import sys

from focus_unittest import TestLoader, TextTestRunner

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
START_DIR = os.path.join(TEST_DIR, 'unit')
VERBOSITY = 1

loader = TestLoader()
tests = loader.discover(START_DIR, 'test_*.py', TEST_DIR)
runner = TextTestRunner(verbosity=VERBOSITY).run(tests)

if runner.wasSuccessful():
    sys.exit(0)
else:
    sys.exit(1)
