""" This module provides the instant messenger plugins that allow for changing
    status messages for a number of popular im programs.
    """

import os
import psutil

from focus import common
from focus.plugin import base

if not common.IS_MACOSX:
    import dbus


## Code Maps ##

PIDGIN_CODE_MAP = {
    'online': 2,     # STATUS_AVAILABLE
    'busy': 3,       # STATUS_UNAVAILABLE
    'away': 5,       # STATUS_AWAY
    'long_away': 6,  # STATUS_EXTENDED_AWAY
    'hidden': 5      # STATUS_AWAY (STATUS_INVISIBLE not supported via DBUS)
}

ADIUM_CODE_MAP = {
    'online': 'available',
    'busy': 'away',
    'away': 'away',
    'long_away': 'away',
    'hidden': 'invisible'
}

EMPATHY_CODE_MAP = {
    'online': ['available'],
    'busy': ['dnd', 'busy'],
    'away': ['away'],
    'long_away': ['xa'],
    'hidden': ['hidden']
}

SKYPE_CODE_MAP = {
    'online': 'ONLINE',
    'busy': 'DND',
    'away': 'AWAY',
    'long_away': 'NA',
    'hidden': 'INVISIBLE'
}


def _dbus_get_object(bus_name, object_name):
    """ Fetches DBUS proxy object given the specified parameters.

        `bus_name`
            Name of the bus interface.
        `object_name`
            Object path related to the interface.

        Returns object or ``None``.
        """

    try:
        bus = dbus.SessionBus()
        obj = bus.get_object(bus_name, object_name)
        return obj

    except (NameError, dbus.exceptions.DBusException):
        return None


def _dbus_get_interface(bus_name, object_name, interface_name):
    """ Fetches DBUS interface proxy object given the specified parameters.

        `bus_name`
            Name of the bus interface.
        `object_name`
            Object path related to the interface.
        `interface_name`
            Name of the interface.

        Returns object or ``None``.
        """

    try:
        obj = _dbus_get_object(bus_name, object_name)
        if not obj:
            raise NameError
        return dbus.Interface(obj, interface_name)

    except (NameError, dbus.exceptions.DBusException):
        return None


def _pidgin_status(status, message):
    """ Updates status and message for Pidgin IM application.

        `status`
            Status type.
        `message`
            Status message.
        """

    try:
        iface = _dbus_get_interface('im.pidgin.purple.PurpleService',
                                    '/im/pidgin/purple/PurpleObject',
                                    'im.pidgin.purple.PurpleInterface')
        if iface:

            # create new transient status
            code = PIDGIN_CODE_MAP[status]
            saved_status = iface.PurpleSavedstatusNew('', code)

            # set the message, if provided
            iface.PurpleSavedstatusSetMessage(saved_status, message)

            # activate status
            iface.PurpleSavedstatusActivate(saved_status)

    except dbus.exceptions.DBusException:
        pass


def _adium_status(status, message):
    """ Updates status and message for Adium IM application.

        `status`
            Status type.
        `message`
            Status message.
        """

    # map status code
    code = ADIUM_CODE_MAP[status]

    # get message
    if not message:
        default_messages = {
            'busy': 'Busy',
            'long_away': 'Extended away'
        }
        message = default_messages.get(status, '')
    else:
        message = message.replace('"', '\\"')  # escape message

    # build applescript
    #  if adium is running:
    #  * set status
    #  * also set status message, if provided
    script = """
     tell application "System Events"
      if exists process "Adium" then
       tell application "Adium" to go {0}""".format(code)

    if message:
        # set status message
        script += ' with message "{0}"'.format(message)

    script += """
      end if
     end tell"""

    # run it
    common.shell_process(['osascript', '-e', script])


def _empathy_status(status, message):
    """ Updates status and message for Empathy IM application.

        `status`
            Status type.
        `message`
            Status message.
        """

    ACCT_IFACE = 'org.freedesktop.Telepathy.Account'
    DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
    ACCT_MAN_IFACE = 'org.freedesktop.Telepathy.AccountManager'
    ACCT_MAN_PATH = '/org/freedesktop/Telepathy/AccountManager'
    SP_IFACE = ('org.freedesktop.Telepathy.'
                'Connection.Interface.SimplePresence')

    # fetch main account manager interface
    am_iface = _dbus_get_interface(ACCT_MAN_IFACE, ACCT_MAN_PATH,
                                   DBUS_PROP_IFACE)

    if am_iface:
        account_paths = am_iface.Get(ACCT_MAN_IFACE, 'ValidAccounts')

        for account_path in account_paths:
            try:
                # fetch account interface
                account = _dbus_get_object(ACCT_MAN_IFACE, account_path)

                # skip disconnected, disabled, etc.
                if account.Get(ACCT_IFACE, 'ConnectionStatus') != 0:
                    continue

                # fetch simple presence interface for account connection
                conn_path = account.Get(ACCT_IFACE, 'Connection')
                conn_iface = conn_path.replace("/", ".")[1:]
                sp_iface = _dbus_get_interface(conn_iface, conn_path,
                                               SP_IFACE)

            except dbus.exceptions.DBusException:
                continue

            # set status and message
            for code in EMPATHY_CODE_MAP[status]:
                try:
                    sp_iface.SetPresence(code, message)
                except dbus.exceptions.DBusException:
                    pass
                else:
                    break


def _linux_skype_status(status, message):
    """ Updates status and message for Skype IM application on Linux.

        `status`
            Status type.
        `message`
            Status message.
        """

    try:
        iface = _dbus_get_interface('com.Skype.API',
                                    '/com/Skype',
                                    'com.Skype.API')
        if iface:
            # authenticate
            if iface.Invoke('NAME focus') != 'OK':
                msg = 'User denied authorization'
                raise dbus.exceptions.DbusException(msg)
            iface.Invoke('PROTOCOL 5')

            # set status
            iface.Invoke('SET USERSTATUS {0}'.format(SKYPE_CODE_MAP[status]))

            # set the message, if provided
            iface.Invoke('SET PROFILE MOOD_TEXT {0}'
                         .format(message))

    except dbus.exceptions.DBusException:
        pass


def _osx_skype_status(status, message):
    """ Updates status and message for Skype IM application on Mac OSX.

        `status`
            Status type.
        `message`
            Status message.
        """

    # XXX: Skype has a bug with it's applescript support on Snow Leopard
    # where it will ignore the "not exists process" expression when
    # combined with "tell application Skype" and thus launches Skype if
    # it's not running. Obviously, this is what we're trying to avoid.
    #
    # The workaround here is to scan the user process list for Skype and
    # bail if we don't find it.

    uid = os.getuid()

    for proc in psutil.process_iter():
        try:
            if proc.uids.real == uid and proc.name == 'Skype':
                skype_running = True
                break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    else:
        skype_running = False

    if skype_running:
        code = SKYPE_CODE_MAP[status]  # map status code
        message = message.replace('"', '\\"')  # escape message

        # build applescript
        #   auto-approve skype security dialog
        #   * hide dialog by setting app hidden
        #   * select allow radio button and click OK on dialog
        #   * restore original app visibility

        #   main loop
        #   * while security dialog is shown or app is loading
        #   ** fetch user status to determine if in pending state
        #   ** run auto-approve if still in pending state

        #   set status command
        #   set status message (mood)

        script = """
         on approve()
          tell application "System Events"
            set vis to the visible of process "Skype"
            set visible of process "Skype" to false
            tell process "Skype"
              set winName to "Skype API Security"
              set rdoBtn to "Allow this application to use Skype"
              if exists (radio button rdoBtn of radio group 1 of window {LC}
              winName) then
                click radio button rdoBtn of radio group 1 of window winName
                delay 0.5
                click button "OK" of window winName
              end if
            end tell
            set visible of process "Skype" to vis
          end tell
         end approve

         tell application "Skype"
          set stat to "COMMAND_PENDING"
          repeat until stat is not equal to "COMMAND_PENDING"
           set stat to send command "GET USERSTATUS" script name "focus"
           if stat is equal to "COMMAND_PENDING" then my approve()
           delay 0.5
          end repeat

          send command "SET USERSTATUS {code}" script name "focus"
          send command "SET PROFILE MOOD_TEXT {mood}" script name "focus"
         end tell""".format(**{
            'code': code,
            'mood': message,
            'LC': "\xc2\xac"
        })

        # run it
        common.shell_process(['osascript', '-e', script])


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
        #       status_msg working, "i'm working.. hello?!";
        #       status_msg lunch, "out to lunch";
        #       status_msg away, "afk";
        #       status away, :working;
        #       status away, "busy as eva!";
        #       end_status online;
        #       timer_status online;
        #   }

        {
            'block': 'im',
            'options': [
                {
                    'name': 'status',
                    'allow_duplicates': False
                },
                {
                    'name': 'end_status',
                    'allow_duplicates': False
                },
                {
                    'name': 'timer_status',
                    'allow_duplicates': False
                },
                {'name': 'status_msg'}
            ]
        }
    ]

    VALID_STATUSES = ('online', 'away', 'long_away', 'busy', 'hidden')

    def __init__(self):
        super(IMStatus, self).__init__()
        self.messages = {}
        self.statuses = {}
        self.set_status_funcs = ()

        if common.IS_MACOSX:
            self.set_status_funcs = (
                _adium_status, _osx_skype_status
            )
        else:
            self.set_status_funcs = (
                _pidgin_status, _empathy_status, _linux_skype_status
            )

    def _set_status(self, status, message=''):
        """ Updates the status and message on all supported IM apps.

            `status`
                Status type (See ``VALID_STATUSES``).
            `message`
                Status message.
            """

        message = message.strip()

        # fetch away message from provided id
        if message.startswith(':'):
            msg_id = message[1:]
            message = self.messages.get(msg_id, '')

        message = message.encode('utf-8', 'replace')

        # attempt to set status for each supported application
        for func in self.set_status_funcs:
            func(status, message)

    def parse_option(self, option, block_name, *values):
        """ Parse status, end_status, timer_status and status_msg options.
            """

        if option.endswith('status'):
            status = values[0]
            if status not in self.VALID_STATUSES:
                raise ValueError(u'Invalid IM status "{0}"'.format(status))

            if len(values) > 2:
                raise TypeError

            if option == 'status':
                option = 'start_' + option

            key = option.split('_', 1)[0]
            self.statuses[key] = values[:2]

        elif option == 'status_msg':
            if len(values) != 2:
                raise TypeError

            name, msg = values
            self.messages[name] = msg

    def on_taskstart(self, task):
        if 'start' in self.statuses:
            self._set_status(*self.statuses['start'])

    def on_taskend(self, task):
        key = 'timer' if task.elapsed else 'end'
        args = self.statuses.get(key)

        if args:
            self._set_status(*args)
