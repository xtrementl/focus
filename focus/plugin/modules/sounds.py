""" This module provides the website-specific event hook plugins that implement
    the 'sites' settings block in the task configuration file.

    The plugin blocks websites during an active task.
    """

import os

from focus import common
from focus.plugin import base


class PlaySound(base.Plugin):
    """ Plays sound files at task start and completion.
        """
    name = 'PlaySound'
    version = '0.1'
    target_version = '>=0.1'
    events = ['task_start', 'task_end']
    options = [
        # Example:
        #   sounds {
        #       play /path/to/file;
        #       end_play /path/to/file;
        #       timer_play /path/to/file;
        #   }

        {
            'block': 'sounds',
            'options': [
                {
                    'name': 'play',
                    'allow_duplicates': False
                },
                {
                    'name': 'end_play',
                    'allow_duplicates': False
                },
                {
                    'name': 'timer_play',
                    'allow_duplicates': False
                }
            ]
        }
    ]

    def __init__(self):
        super(PlaySound, self).__init__()
        self.files = {}

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

    def parse_option(self, option, block_name, *values):
        """ Parse options for play, end_play, and timer_play.
            """

        if len(values) != 1:
            raise TypeError
        value = os.path.realpath(os.path.expanduser(values[0]))

        if not os.path.isfile(value) and not os.path.islink(value):
            raise ValueError(u'Sound file "{0}" does not exist'
                             .format(value))

        # special extension check for aplay player
        ext = os.path.splitext(value)[1].lower()
        if ext != 'wav' and self._get_external_player() == 'aplay':
            raise ValueError(u"Only WAV sound file "
                             "supported for 'aplay'")

        if option == 'play':
            option = 'start_' + option

        key = option.split('_', 1)[0]
        self.files[key] = value

    def on_taskstart(self, task):
        """ Play sounds at task start.
            """
        if 'start' in self.files:
            self._play_sound(self.files['start'])

    def on_taskend(self, task):
        """ Play sounds at task end.
            """
        key = 'timer' if task.elapsed else 'end'
        filename = self.files.get(key)

        if filename:
            self._play_sound(filename)
