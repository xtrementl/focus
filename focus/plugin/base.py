""" This module provides the ``Plugin`` metaclass that auto-registers new
    plugins into the system using the `registration` module.
    """

import focus.version
from focus.plugin import registration


_REQUIRED_ATTRIBS = ('name', 'version', 'target_version')


class _PluginMeta(type):
    """ Plugin metaclass that automatically registers plugin classes if they
        extend from the supported bases classes and implement the required
        class attributes.
        """

    def __init__(cls, name, bases, attrs):
        """ Class definition is initialized: checks for required attributes and
            registers the plugin class if it passes all checks.
            """

        super(_PluginMeta, cls).__init__(name, bases, attrs)

        # check if class is instance of meta base
        if any([b for b in bases if isinstance(b, _PluginMeta)]):  # parents
            # Doesn't have all the required attributes, bail.
            for attr in _REQUIRED_ATTRIBS:
                if not attrs.get(attr):
                    return

            # must define at least one
            command = attrs.get('command')
            if not attrs.get('events') and not command:
                return

            if command:
                # must be a string
                if not isinstance(command, basestring):
                    return

                # and not empty. strip spaces from class's command name
                cls.command = cls.command.strip()
                if not cls.command:
                    return

            # check plugin target version against program version
            if not focus.version.compare_version(attrs['target_version']):
                return

            # if we made it this far, then it's a valid plugin:
            # let's add it to the registries
            registration.register_all(cls)


class Plugin(object):
    """ Base plugin class that provides all the supported attributes necessary
        for the metaclass, ``PluginMeta``.
        """

    __metaclass__ = _PluginMeta

    #--------------------------
    #: Supported Attributes
    #--------------------------

    #: Plugin Name (string): Must be unique. Required.
    name = None

    #: Version (string): (e.g. '1.0'). Required.
    version = None

    #: Target Focus Version (string): (e.g. '>=0.1'). Required.
    #:   Supported operators: <,<=,==,>, or >=
    target_version = None

    #: Command Name (string): Must be unique. Required, if 'events' not set.
    command = None

    #: Event Hooks (tuple,list): List of strings.
    #:                           Required, if 'command' not set.
    #:
    #:   task_start - Calls `on_taskstart` method when a new task is started.
    #:
    #:   task_run   - Calls `on_taskrun` method during the main program loop
    #:                while a task is active. This method should yield to
    #:                other plugins hooking the same event, so cpu-intensive
    #:                tasks should be performed in another thread.
    #:
    #:   task_end   - Calls `on_taskend` method when an active task has ended.
    #:
    events = None

    #: Option Hooks (tuple,list): List of strings or nested lists of strings.
    #:   This allows the plugin to register options in task configuation files.
    #:   String values are non-block options, while list or tuple values with
    #:   nested string values represent block options.
    #:
    #:   This calls the 'parse_option' method with the specified basic and
    #:   block options.
    #:
    #:   Example::
    #:       ( 'non_block_option', ('block_name', ('option_1', 'option_2')) )
    #:
    options = None

    #: Root Access (boolean): Set to ``True`` if this plugin needs access to
    #: the `run_root` command to run arbitrary shell commands as the root user.
    #:
    #:   The plugin will be provided a class method `run_root()` with the
    #:   following interface::
    #:       run_root(self, command).
    #:
    #: The `command` argument will be shell escaped automatically.
    #: The method returns boolean.
    #:
    needs_root = False

    #: Task Only (boolean): Set to ``True`` if this plugin should only be
    #: available when a task is active.
    #:
    task_only = False

    #--------------------------
    #: Class Utilities
    #--------------------------

    def disable(self):
        """ Prevents this plugin from running hereafter.
            """
        registration.disable_plugin_instance(self)

    #--------------------------
    #: Event Hook Specifics
    #--------------------------

    def on_taskstart(self, task):
        """ Event hook that is called upon start of a task.

            `task`
                ``Task`` instance.
            """
        pass

    def on_taskrun(self, task):
        """ Event hook that is called within the main event loop during an
            active task.

            `task`
                ``Task`` instance.

            Note, this method is called in a chain of plugins, so cpu-intensive
            processing should be yielded to another thread of execution so
            other plugins aren't negatively affected.
            """
        pass

    def on_taskend(self, task):
        """ Event hook that is called when task has ended.

            `task`
                ``Task`` instance.
            """
        pass

    #--------------------------
    #: Option Hook Specifics
    #--------------------------

    def parse_option(self, option, block_name, *values):
        """ This hook is called during the task config parsing stage, before
            loading a ``Task`` object.

            `option`
                Name of option being parsed.
            `block_name`
                Name of parent block for the current option.
                Note, this will be ``None`` for non-block options.

            `*values`
                One or more values associated with the current option.
            """
        pass

    #--------------------------
    #: Command Hook Specifics
    #--------------------------

    def setup_parser(self, parser):
        """ This is called when setting up argument parser for command
            arguments. Override this to modify parser setup.

            `parser`
                ``FocusArgParser`` object.
            """
        pass

    def execute(self, env, args):
        """ This hook is called when executed on the command-line for the
            defined command hook value.

            `env`
                ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """
        pass
