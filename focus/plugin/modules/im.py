""" This module provides the instant messenger plugins that allow for changing
    status messages for a number of popular im programs.
    """

from focus.plugin import base


class IMStatus(base.Plugin):
    """ Changes the status for an instant-messenger client.
        """
    name = 'IMStatus'
    version = '0.1'
    target_version = '>=0.1'
    events = ['task_start', 'task_end']
    options = [
        # Example:
        #   im {
        #       away_msg working, "i'm working.. hello?!";
        #       away_msg lunch, "out to lunch";
        #       away_msg away, "afk";
        #       status away, :working; # or "away message"
        #       end_status online;
        #       timer_status online;
        #   }

        {
            'block': 'im',
            'options': [
                {
                    'name': 'start_status',
                    'allow_duplicates': False
                },
                {
                    'name': 'end_status',
                    'allow_duplicates': False
                },
                {'name': 'away_msg'}
            ]
        }
    ]

    def __init__(self):
        super(Timer, self).__init__()
        self.statuses = {}
        self.away_messages = {}

    def _set_status(self, status, message=None):
        if status == 'away':
            if message:
                message = message.strip()

                # fetch away message from provided id
                if message.startswith(':'):
                    away_msg_id = message[1:]
                    message = self.away_messages.get(away_msg_id)

        # TODO: set status

    def parse_option(self, option, block_name, *values):
        """ Parse status, end_status, timer_status and away_msg options.
            """

        if option in ('status', 'end_status', 'timer_status'):
            status = values[0]
            if status not in ('online', 'hidden', 'away'):
                raise ValueError(u'Invalid IM status "{0}"'.format(status))

            max_len = 2 if status == 'away' else 1
            if len(values) != max_len:
                raise TypeError

            if option == 'status':
                option = 'start_' + option

            key = option.split('_', 1)[0]
            self.statuses[key] = values[:max_len]

        elif option == 'away_msg':
            if len(values) != 2:
                raise TypeError
            name, msg = values

            if name in self.away_messages:
                raise ValueError(u'IM away message already defined "{0}"'
                                 .format(name))
            self.away_messages[name] = msg

    def on_taskstart(self, task):
        if 'start' in self.statuses:
            self._set_status(*self.statuses['start'])

    def on_taskend(self, task):
        key = 'timer' if task.elapsed else 'end'
        args = self.statuses.get(key)

        if args:
            self._set_status(*args)
