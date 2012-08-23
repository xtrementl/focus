""" This module provides the notification plugin that allows for
    showing system notification messages.
    """

from focus import common
from focus.plugin import base

if not common.IS_MACOSX:
    import dbus


def _terminal_notifier(title, message):
    """ Shows user notification message via `terminal-notifier` command.

        `title`
            Notification title.
        `message`
            Notification message.
        """

    try:
        paths = common.extract_app_paths(['terminal-notifier'])
    except ValueError:
        pass

    common.shell_process([paths[0], '-title', title, '-message', message])


def _growlnotify(title, message):
    """ Shows growl notification message via `growlnotify` command.

        `title`
            Notification title.
        `message`
            Notification message.
        """

    try:
        paths = common.extract_app_paths(['growlnotify'])
    except ValueError:
        return

    common.shell_process([paths[0], '-t', title, '-m', message])


def _osx_popup(title, message):
    """ Shows a popup dialog message via System Events daemon.

        `title`
            Notification title.
        `message`
            Notification message.
        """

    message = message.replace('"', '\\"')  # escape message

    # build applescript
    script = """
     tell application "System Events"
       display dialog "{0}"
     end tell""".format(message)

    # run it
    common.shell_process(['osascript', '-e', script])


def _dbus_notify(title, message):
    """ Shows system notification message via dbus.

        `title`
            Notification title.
        `message`
            Notification message.
        """

    try:
        # fetch main account manager interface
        bus = dbus.SessionBus()
        obj = bus.get_object('org.freedesktop.Notifications',
                             '/org/freedesktop/Notifications')
        if obj:
            iface = dbus.Interface(obj, 'org.freedesktop.Notifications')

            if iface:
                # dispatch notification message
                iface.Notify('Focus', 0, '', title, message, [], {}, 5)

    except dbus.exceptions.DBusException:
        pass


class Notify(base.Plugin):
    """ Shows system notification messages.
        """
    name = 'Notify'
    version = '0.1'
    target_version = '>=0.1'
    events = ['task_start', 'task_end']
    options = [
        # Example:
        #   notify {
        #       show "message";
        #       end_show "message";
        #       timer_show "message";
        #   }

        {
            'block': 'notify',
            'options': [
                {
                    'name': 'show',
                    'allow_duplicates': False
                },
                {
                    'name': 'end_show',
                    'allow_duplicates': False
                },
                {
                    'name': 'timer_show',
                    'allow_duplicates': False
                }
            ]
        }
    ]

    def __init__(self):
        super(Notify, self).__init__()
        self.messages = {}
        self.notify_func = None

        if common.IS_MACOSX:
            commands = ['terminal-notifier', 'growlnotify']

            while commands:
                try:
                    command = command.pop()
                    common.extract_app_paths(command)
                except ValueError:
                    continue

                if command == 'terminal-notifier':
                    self.notify_func = _terminal_notifier
                else:
                    self.notify_func = _growlnotify
                break  # found one

            # fallback to popup dialog
            if not self.notify_func:
                self.notify_func = _osx_popup

        else:
            self.notify_func = _dbus_notify

    def _notify(self, task, message):
        """ Shows system notification message according to system requirements.

            `message`
                Status message.
            """

        if self.notify_func:
            message = common.to_utf8(message.strip())
            title = common.to_utf8(u'Focus ({0})'.format(task.name))
            self.notify_func(title, message)

    def parse_option(self, option, block_name, message):
        """ Parse show, end_show, and timer_show options.
            """

        if option == 'show':
            option = 'start_' + option

        key = option.split('_', 1)[0]
        self.messages[key] = message

    def on_taskstart(self, task):
        if 'start' in self.messages:
            self._notify(task, self.messages['start'])

    def on_taskend(self, task):
        key = 'timer' if task.elapsed else 'end'
        message = self.messages.get(key)

        if message:
            self._notify(task, message)
