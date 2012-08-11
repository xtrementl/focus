""" This module provides the website-specific event hook plugins that implement
    the 'sites' settings block in the task configuration file.

    The plugin blocks websites during an active task.
    """

import os
import re
import urlparse
import tempfile

from focus import common
from focus.plugin import base


_RE_PROTOCOL = re.compile(r'(?:(ht|f)tp(s?)\:\/\/)')
_RE_TLD = re.compile(r'((?:\.[a-zA-Z]{2,6}){1,2})$')
_RE_WWW_SUB = re.compile(r'^www\.')


class SiteBlock(base.Plugin):
    """ Blocks websites during an active task.
        """
    name = 'SiteBlock'
    version = '0.1'
    target_version = '>=0.1'
    needs_root = True   # so we can update hosts file
    events = ['task_run', 'task_end']
    options = [
        # Example:
        #   sites {
        #       block youtube.com, "http://www.reddit.com", www.foursquare.com;
        #       block news.ycombinator.com, twitter.com, "www.facebook.com";
        #   }

        {
            'block': 'sites',
            'options': [
                {'name': 'block'}
            ]
        }
    ]

    def __init__(self):
        super(SiteBlock, self).__init__()
        self.domains = set()
        self.hosts_file = '/etc/hosts'
        self.last_updated = -1
        self.orig_data = None

    def _handle_block(self, task, disable=False):
        """ Handles blocking domains using hosts file.

            `task`
                ``Task`` instance.

            `disable`
                Set to ``True``, to turn off blocking and restore hosts file;
                otherwise, ``False`` will enable blocking by updating hosts
                file.

            Returns boolean.
            """

        backup_file = os.path.join(task.task_dir, '.hosts.bak')
        self.orig_data = self.orig_data or common.readfile(backup_file)
        self.last_updated = self.last_updated or -1

        if not self.orig_data:
            # should't attempt restore without good original data, bail
            if disable:
                return False

            # attempt to fetch data from the source
            self.orig_data = common.readfile(self.hosts_file)
            if not self.orig_data:
                return False

        # restore backup
        if not os.path.exists(backup_file):
            common.writefile(backup_file, self.orig_data)

        # bail early if hosts file modification time hasn't changed
        try:
            should_write = (disable or self.last_updated
                            != os.path.getmtime(self.hosts_file))

        except OSError:
            should_write = True  # file was removed, let's write!

        if not should_write:
            return True

        # make copy of original data, in case we need to modify
        data = self.orig_data

        # if not restoring, tack on domains mapped
        # to localhost to end of file data
        if not disable:
            # convert the set to a list and sort
            domains = list(self.domains)
            domains.sort()

            data += ('\n'.join('127.0.0.1\t{0}\t# FOCUS'
                     .format(d) for d in domains) + '\n')

        # make temp file with new host file data
        with tempfile.NamedTemporaryFile(prefix='focus_') as tempf:
            tempf.write(data)
            tempf.flush()

            # overwrite hosts file with our modified copy.
            if not self.run_root('cp "{0}" "{1}"'.format(tempf.name,
                                                         self.hosts_file)):
                return False

            # MacOS X generally requires flushing the system dns cache to pick
            # up changes to the hosts file:
            #   dscacheutil -flushcache or lookupd -flushcache
            if common.IS_MACOSX:
                dscacheutil, lookupd = [common.which(x) for x in
                                        ('dscacheutil', 'lookupd')]
                self.run_root(' '.join([dscacheutil or lookupd,
                                        '-flushcache']))

        if disable:
            common.safe_remove_file(backup_file)  # cleanup the backup

        # store last modification time
        try:
            self.last_updated = os.path.getmtime(self.hosts_file)

        except OSError:
            # file was removed, let's update next time around
            self.last_updated = -1

        return True

    def parse_option(self, option, block_name, *values):
        """ Parse domain values for option.
            """
        _extra_subs = ('www', 'm', 'mobile')

        if len(values) == 0:  # expect some values here..
            raise ValueError

        for value in values:
            value = value.lower()

            # if it doesn't look like a protocol, assume http
            # (e.g. only domain supplied)
            if not _RE_PROTOCOL.match(value):
                value = 'http://' + value

            # did it parse? pull hostname/domain
            parsed = urlparse.urlparse(value)
            if parsed:
                domain = parsed.hostname

                if domain and _RE_TLD.search(domain):  # must have a TLD
                    # doesn't have subdomain, tack on www, m, and mobile
                    # for good measure. note, this check fails for
                    # multi-part TLDs, e.g. .co.uk
                    domain = _RE_WWW_SUB.sub('', domain)  # strip "www."

                    if len(domain.split('.')) == 2:
                        for sub in _extra_subs:
                            self.domains.add('{0}.{1}'.format(sub, domain))

                    self.domains.add(domain)

        # no domains.. must have failed
        if not self.domains:
            raise ValueError

    def on_taskrun(self, task):
        self._handle_block(task)

    def on_taskend(self, task):
        self._handle_block(task, disable=True)
