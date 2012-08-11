""" This module provides the task timer event/command plugin that allows
    for automatically ending an active task after a designated time period.
    """

from focus import common
from focus.plugin import base


class Timer(base.Plugin):
    """ Displays remaining time for the active task.
        """
    name = 'Timer'
    version = '0.1'
    target_version = '>=0.1'
    command = 'left'
    events = ['task_start']
    options = [
        # --------------------------------
        # Timer duration for task
        # --------------------------------
        # Example: duration 30;

        {
            'name': 'duration',
            'allow_duplicates': False
        }
    ]

    def __init__(self):
        super(Timer, self).__init__()
        self.total_duration = 0

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('-s', '--short', action='store_true')

    def execute(self, env, args):
        """ Displays task time left in minutes.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        msg = u'Time Left: {0}m' if not args.short else '{0}'
        mins = max(0, self.total_duration - env.task.duration)
        env.io.write(msg.format(mins))

    def parse_option(self, option, block_name, *values):
        """ Parse duration option for timer.
            """

        try:
            if len(values) != 1:
                raise TypeError

            self.total_duration = int(values[0])
            if self.total_duration <= 0:
                raise ValueError

        except ValueError:
            pattern = u'"{0}" must be an integer > 0'
            raise ValueError(pattern.format(option))

    def on_taskstart(self, task):
        """ Set the total task duration.
            """

        if self.total_duration:
            task.set_total_duration(self.total_duration)
