""" This module defines all the exceptions that are specific to this system.
    """

import os

from focus import common


__all__ = ('FocusError', 'HelpBanner', 'DirectorySetupFail' 'PluginImport',
           'UserPluginImport', 'ActiveTask', 'NoActiveTask', 'TaskNotFound',
           'InvalidTaskConfig', 'NoPluginsRegistered', 'DaemonFailStart')


class FocusError(Exception):
    """ Base Focus Exception.
        """

    def __init__(self, description=None, code=None):
        """ Class init.

            `description`
                Error description string.
            `code`
                Exit status code. ``Default: 2``
            """

        super(FocusError, self).__init__(description)

        if not description is None:
            self.description = description
        else:
            self.description = getattr(self, 'description', None)
        if self.description:
            self.description = common.from_utf8(self.description)

        if not code is None:
            self.code = code
        else:
            self.code = getattr(self, 'code', None) or 2

    def __str__(self):
        return common.to_utf8(self.description)

    def __unicode__(self):
        return self.description


class HelpBanner(FocusError):
    """ Pseudo-error to handle printing help banner for CLI.
        """
    code = 1
    description = u'Help banner'


class DirectorySetupFail(FocusError):
    """ Could not create user data or daemon directories.
        """
    code = 200
    description = u'Error creating directories'


class PluginImport(FocusError):
    """ An error occurred while loading a plugin.
        """
    code = 201

    def __init__(self, description=None):
        self.description = u'Error importing core plugins'

        if description:
            self.description += u': ' + common.from_utf8(description)

        super(PluginImport, self).__init__(self.description)


class UserPluginImport(PluginImport):
    """ An error occurred while loading a user plugin.
        """
    code = 202

    def __init__(self, description=None):
        self.description = u'Error importing user plugins'

        if description:
            self.description += u': ' + common.from_utf8(description)

        super(UserPluginImport, self).__init__(self.description)


class ActiveTask(FocusError):
    """ An active task is already running.
        """
    code = 203
    description = u'Cannot perform action while a task is active'


class NoActiveTask(FocusError):
    """ No active task is running.
        """
    code = 204
    description = u'No active task found'


class TaskNotFound(FocusError):
    """ Specified task does not exist.
        """
    code = 205

    def __init__(self, task_name):
        self.description = (u'Task "{0}" does not exist'
                            .format(common.from_utf8(task_name)))

        super(TaskNotFound, self).__init__(self.description)


class TaskExists(FocusError):
    """ Specified task already exists.
        """
    code = 206

    def __init__(self, task_name):
        self.description = (u'Task "{0}" already exists'
                            .format(common.from_utf8(task_name)))

        super(TaskExists, self).__init__(self.description)


class InvalidTaskConfig(FocusError):
    """ Specified task configuration file is an invalid format.
        """
    code = 207

    def __init__(self, filename, reason):
        self.filename = common.from_utf8(filename)
        self.reason = common.from_utf8(reason)
        self.description = (u'Invalid task config "{0}",{1}   reason: {2}'
                            .format(filename, os.linesep, reason))

        super(InvalidTaskConfig, self).__init__(self.description)


class NoPluginsRegistered(FocusError):
    """ No plugins were registered.
        """
    code = 208
    description = u'No plugins registered'


class DaemonFailStart(FocusError):
    """ Daemon process failed to start.
        """
    code = 209
    description = u'Error starting focusd daemon'
