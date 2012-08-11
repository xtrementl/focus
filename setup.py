#!/usr/bin/env python
import os
import sys
from distutils.core import setup

# compile for version info
execfile('focus/version.py')

requires = ['psutil >= 0.4.1']
if sys.version_info[0:2] < (2, 7):
    requires.append('argparse')

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
long_desc = f.read()
f.close()

setup(
    name='focus',
    version=__version__,
    description=('Command-line productivity tool '
                 'for improved task workflows.'),
    long_description=long_desc,
    keywords='focus',
    license='MIT',
    author='Erik Johnson',
    author_email='xtrementl@brokenresolve.com',
    url='https://github.com/xtrementl/focus',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: Utilities'],
    packages=['focus',
              'focus.environment',
              'focus.parser',
              'focus.plugin',
              'focus.plugin.modules'],
    scripts=['scripts/focus',
             'scripts/focusd'],
    data_files=[('/etc', ['conf/focus_task.cfg'])],
    install_requires=requires
)
