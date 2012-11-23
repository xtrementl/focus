""" This module provides a simple task monitoring capability to track usage
    statistics for tasks.
    """

import re
import os
import datetime

try:
    import simplejson as json
except ImportError:
    import json

from focus.plugin import base
from focus import common, errors

MINS_IN_HOUR = 60
MINS_IN_DAY = MINS_IN_HOUR * 24


class Stats(base.Plugin):
    """ Prints usage statistics about tasks.
        """
    name = 'Stats'
    version = '0.1'
    target_version = '>=0.1'
    events = ['task_end']
    command = 'stat'

    def _sdir(self, base_dir):
        """ Return path to stats directory.

            `base_dir`
                Base directory.

            Returns string.
            """
        return os.path.join(base_dir, '.stats')

    def _setup_dir(self, base_dir):
        """ Creates stats directory for storing stat files.

            `base_dir`
                Base directory.
            """
        stats_dir = self._sdir(base_dir)

        if not os.path.isdir(stats_dir):
            try:
                os.mkdir(stats_dir)
            except OSError:
                raise errors.DirectorySetupFail()

    def _log_task(self, task):
        """ Logs task record to file.

            `task`
                ``Task`` instance.
            """
        if not task.duration:
            return

        self._setup_dir(task.base_dir)
        stats_dir = self._sdir(task.base_dir)
        duration = task.duration

        while duration > 0:
            # build filename
            date = (datetime.datetime.now() -
                    datetime.timedelta(minutes=duration))
            date_str = date.strftime('%Y%m%d')
            filename = os.path.join(stats_dir, '{0}.json'.format(date_str))

            with open(filename, 'a+') as file_:
                # fetch any existing data
                try:
                    file_.seek(0)
                    data = json.loads(file_.read())
                except (ValueError, OSError):
                    data = {}

                if not task.name in data:
                    data[task.name] = 0

                # how much total time for day
                try:
                    total_time = sum(int(x) for x in data.values())
                    if total_time > MINS_IN_DAY:
                        total_time = MINS_IN_DAY

                except ValueError:
                    total_time = 0

                # constrain to single day
                amount = duration
                if amount + total_time > MINS_IN_DAY:
                    amount = MINS_IN_DAY - total_time

                    # invalid or broken state, bail
                    if amount <= 0:
                        break

                data[task.name] += amount
                duration -= amount

                # write file
                try:
                    file_.seek(0)
                    file_.truncate(0)
                    file_.write(json.dumps(data))
                except (ValueError, OSError):
                    pass

    def _fuzzy_time_parse(self, value):
        """ Parses a fuzzy time value into a meaningful interpretation.

            `value`
                String value to parse.
            """

        value = value.lower().strip()
        today = datetime.date.today()

        if value in ('today', 't'):
            return today

        else:
            kwargs = {}

            if value in ('y', 'yesterday'):
                kwargs['days'] = -1

            elif value in ('w', 'wk', 'week', 'last week'):
                kwargs['days'] = -7

            else:
                # match days
                match = re.match(r'(\d+)\s*(d|day|days)\s*(ago)?$', value)
                if match:
                    kwargs['days'] = -int(match.groups(1)[0])

                else:
                    # match weeks
                    match = re.match(r'(\d+)\s*(w|wk|week|weeks)\s*(ago)?$',
                                     value)
                    if match:
                        kwargs['weeks'] = -int(match.groups(1)[0])

            if kwargs:
                return today + datetime.timedelta(**kwargs)

            return None

    def _get_stats(self, task, start_date):
        """ Fetches statistic information for given task and start range.
            """

        stats = []
        stats_dir = self._sdir(task.base_dir)
        date = start_date
        end_date = datetime.date.today()
        delta = datetime.timedelta(days=1)

        while date <= end_date:
            date_str = date.strftime('%Y%m%d')
            filename = os.path.join(stats_dir, '{0}.json'.format(date_str))

            if os.path.exists(filename):
                try:
                    # fetch stats content
                    with open(filename, 'r') as file_:
                        data = json.loads(file_.read())

                    # sort descending by time
                    stats.append((date, sorted(data.iteritems(),
                                               key=lambda x: x[1],
                                               reverse=True)))

                except (json.JSONDecodeError, OSError):
                    pass

            date += delta  # next day

        return stats

    def _print_stats(self, env, stats):
        """ Prints statistic information using io stream.

            `env`
                ``Environment`` object.
            `stats`
                Tuple of task stats for each date.
            """

        def _format_time(mins):
            """ Generates formatted time string.
                """
            mins = int(mins)

            if mins < MINS_IN_HOUR:
                time_str = '0:{0:02}'.format(mins)
            else:
                hours = mins // MINS_IN_HOUR
                mins %= MINS_IN_HOUR

                if mins > 0:
                    time_str = '{0}:{1:02}'.format(hours, mins)
                else:
                    time_str = '{0}'.format(hours)

            return time_str

        if not stats:
            env.io.write('No stats found.')
            return

        for date, tasks in stats:
            env.io.write('')
            total_mins = float(sum(v[1] for v in tasks))
            env.io.write('[ {0} ]'.format(date.strftime('%Y-%m-%d')))
            env.io.write('')

            for name, mins in tasks:
                # format time
                time_str = _format_time(mins)

                # generate stat line
                line = '   {0:>5}'.format(time_str)
                line += ' ({0:2.0f}%) - '.format(mins * 100.0 / total_mins)
                if len(name) > 55:
                    name = name[:55] + '...'
                line += name
                env.io.write(line)

            # generate total line
            env.io.write('_' * len(line))
            time_str = _format_time(total_mins)
            env.io.write('   {0:>5} (total)'.format(time_str))
            env.io.write('')

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('start', nargs='?',
                            help='starting period. defaults to today',
                            default='today')

    def execute(self, env, args):
        """ Prints task information.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        start = self._fuzzy_time_parse(args.start)
        if not start:
            raise errors.FocusError(u'Invalid start period provided')

        stats = self._get_stats(env.task, start)
        self._print_stats(env, stats)

    def on_taskend(self, task):
        """ Logs task usage stats when task ends.
            """
        self._log_task(task)
