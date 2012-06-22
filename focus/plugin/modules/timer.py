""" This module provides the task timer event and command plugins that allow
    for automatically ending an active task after a designated time period
    and executing custom actions thereafter.
    """

import os
import sys
import time

from focus import common
from focus.plugin import base


class Timer(base.Plugin):
    """ Displays remaining time for the active task.
        """
    name = 'Timer'
    version = '0.1'
    target_version = '>=0.1'
    command = 'left'
    events = ['task_run', 'task_end']
    options = [
        # --------------------------------
        # Timer duration for task
        # --------------------------------
        # Example: duration 30;

        {
            'name': 'duration',      
            'allow_duplicates': False
        },

        # --------------------------------
        # Actions when timer elapses
        # --------------------------------
        # Example:
        #   timer_actions {
        #       play /path/to/file;
        #       run /path/to/file,
        #           /another/path/to/file;
        #   }

        {
            'block': 'timer_actions',
            'options': [
                {
                    'name': 'play',
                    'allow_duplicates': False
                },
                {
                    'name': 'run'
                }
            ]
        },

        # --------------------------------
        # Actions when task manually ended
        # --------------------------------
        # Example:
        #   end_actions {
        #       play /path/to/file;
        #       run /path/to/file;
        #   }

        {
            'block': 'end_actions',
            'options': [
                {
                    'name': 'play',
                    'allow_duplicates': False
                },
                { 'name': 'run' }
            ]
        }
    ]

    def __init__(self):
        super(Timer, self).__init__()
        self.total_duration = 0
        self.actions = {}
        self.elapsed = False

    def _get_external_player(self):
        """ Determines external sound player to available.

            Returns string or ``None``.
            """

        if common.IS_MACOSX:
            return 'afplay'

        else:
            for name in ('mpg123', 'play', 'aplay'):
                if common.which(name):
                    return name
        return None  # couldn't find a player

    def _play_sound(self, filename):
        """ Shells player with the provided filename.
            
            `filename`
                Filename for sound file.
            """

        command = self._get_external_player()
        if not command:
            return  # no player found

        if common.IS_MACOSX:
            command += ' "{0}"'.format(filename)
        else:
            # append quiet flag and filename
            is_play = (command == 'play')
            command += ' -q "{0}"'.format(filename)

            # HACK: play can default to using pulseaudio. here, we
            # check if pulse command exists and delegate to alsa if
            # not
            if is_play and not common.which('pulseaudio'):
                command += ' -t alsa'

        # play sound file, ignore if it fails
        common.shell_process(command, background=True)

    def _run_apps(self, paths):
        """ Runs applications for the provided paths.

            `paths`
                List of shell commands
            """

        for path in paths:
            common.shell_process(path, background=True)
            time.sleep(0.2)  # delay some between starts

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
        """ Parse duration option and end_action block options.
            """

        if not block_name and option == 'duration':
            try:
                if len(values) != 1:
                    raise TypeError

                self.total_duration = int(values[0])
                if self.total_duration <= 0:
                    raise ValueError

            except ValueError:
                pattern = u'"{0}" must be an integer > 0'
                raise ValueError(pattern.format(option))

        elif block_name in ('timer_actions', 'end_actions'):
            action = block_name.replace('actions', '') + option

            if option == 'play':  # play sound
                if len(values) != 1:
                    raise TypeError
                value = os.path.realpath(values[0])

                if not os.path.isfile(value) and not os.path.islink(value):
                    raise ValueError(u'Sound file "{0}" does not exist'
                                     .format(value))

                # special extension check for aplay player
                ext = os.path.splitext(value)[1].lower()
                if ext != 'wav' and self._get_external_player() == 'aplay':
                    raise ValueError(u"Only WAV sound file "
                                      "supported for 'aplay'")

                self.actions[action] = value

            elif option == 'run':  # run apps
                if not action in self.actions:
                    self.actions[action] = set()

                paths = common.extract_app_paths(values)
                self.actions[action].update(paths)

    def on_taskrun(self, task):
        """ If task duration has exceeded duration setting, end this task.
            """

        if self.total_duration > 0 and task.duration >= self.total_duration:
            self.elapsed = True
            task.stop()

    def on_taskend(self, task):
        """ If time elapsed, run any end or timer actions.
            """

        for action, value in self.actions.iteritems():
            type_, action = action.split('_')

            if (type_ == 'timer' and self.elapsed
                or type_ == 'end' and not self.elapsed):

                if action == 'play':
                    self._play_sound(value)

                elif action == 'run':
                    self._run_apps(value)
