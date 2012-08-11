""" This module manages the registration for plugins in the system.

    It provides interfaces to store, query, and update existing registries that
    are used throughout the system to support custom command-line commands,
    task events hooks, and configurable per-task plugin settings.
    """

import types

from focus import common, registry, errors

__all__ = ('register', 'deregister', 'register_all', 'setup_sudo_access',
           'get_registered', 'get_command_hook', 'run_event_hooks',
           'run_option_hooks')


_event_hooks = {}
_command_hooks = registry.Registry()
_option_hooks = registry.ExtRegistry()
_registered = registry.ExtRegistry()  # all installed plugins

_EVENT_VALS = ('task_start', 'task_run', 'task_end')


def _is_plugin_disabled(plugin):
    """ Determines if provided plugin is disabled from running for the
        active task.
        """
    item = _registered.get(plugin.name)
    if not item:
        return False

    _, props = item
    return bool(props.get('disabled'))


def _setup_command(plugin):
    """ Handles setup or teardown of command hook registration for the provided
        plugin.

        `plugin`
            ``Plugin`` class.
        """

    if plugin.command:
        register('command', plugin.command, plugin)


def _setup_events(plugin):
    """ Handles setup or teardown of event hook registration for the provided
        plugin.

        `plugin`
            ``Plugin`` class.
        """

    events = plugin.events

    if events and isinstance(events, (list, tuple)):
        for event in [e for e in events if e in _EVENT_VALS]:
            register('event', event, plugin)


def _setup_options(plugin):
    """ Handles setup or teardown of option hook registration for the provided
        plugin.

        `plugin`
            ``Plugin`` class.
        """

    options = plugin.options

    if options and isinstance(options, (list, tuple)):
        for props in options:
            if isinstance(props, dict):
                if 'block' in props and 'options' in props:  # block
                    block = props['block']
                    option_list = props['options']

                    # options for this block
                    for props in option_list:
                        if isinstance(props, dict):
                            name = props.pop('name', None)

                            if name:
                                key = "{0}_{1}".format(block, name)
                                register('option', key, plugin, props)

                else:  # non-block option
                    name = props.pop('name', None)

                    if name:
                        register('option', name, plugin, props)


def disable_plugin_instance(plugin):
    """ Marks a plugin instance as disabled.

        `plugin`
            ``Plugin`` instance.
        """
    _registered.register(plugin.name, plugin.__class__, {'disabled': True})


def register(hook_type, key, plugin_cls, properties=None):
    """ Handles registration of a plugin hook in the global registries.

        `hook_type`
            Type of hook to register ('event', 'command', or 'option')
        `key`
            Unique key associated with `hook_type` and `plugin`.
            Value depends on type::
                'command' - Name of the command

                'event'   - Name of the event to associate with plugin:
                                ('task_start', 'task_run', 'task_end')

                'option'  - Option name for task config file. Name should be
                            prefixed with block name if it has one:
                            (e.g. apps_startpath)
        `plugin_cls`
            ``Plugin`` class.
        `properties`
            Dictionary with properties related to provided plugin and key.

        Note, upon registration of any hooks, the plugin will also be
        registered in the master plugin registry.
        """

    def fetch_plugin():
        """ This function is used as a lazy evaluation of fetching the
            specified plugin. This is required, because at the time of
            registration of hooks (metaclass creation), the plugin class won't
            exist yet in the class namespace, which is required for the
            `Registry.get()` method. One benefit of this implementation is that
            we can reference the same object instance in each of the hook
            registries instead of making a new instance of the plugin for every
            registry that links to the same plugin.
            """
        return _registered.get(plugin_cls.name)[0]  # extended, strip type info

    # type information for plugin in main registry
    type_info = {}

    # register a command for plugin
    if hook_type == 'command':
        _command_hooks.register(key, fetch_plugin)
        type_info['command'] = True

    # register event chain for plugin
    elif hook_type == 'event':
        if not key in _event_hooks:
            _event_hooks[key] = []
        _event_hooks[key].append((plugin_cls.name, fetch_plugin))
        type_info['event'] = True

    # register an option for plugin
    elif hook_type == 'option':
        _option_hooks.register(key, fetch_plugin, properties or {})
        type_info['option'] = True

    else:
        return

    # register this class in main registry
    _registered.register(plugin_cls.name, plugin_cls, type_info)


def register_all(plugin_cls):
    """ Handles setup or teardown of all hook types for the provided plugin.

        `plugin_cls`
            ``Plugin`` class.
        """

    for fn_ in (_setup_command, _setup_events, _setup_options):
        fn_(plugin_cls)


def setup_sudo_access(plugin):
    """ Injects a `run_root` method into the provided plugin instance that
        forks a shell command using sudo. Used for command plugin needs.

        `plugin`
            ``Plugin`` instance.
        """

    def run_root(self, command):
        """ Executes a shell command as root.

            `command`
                Shell command string.

            Returns boolean.
            """
        try:
            return not (common.shell_process('sudo ' + command) is None)

        except KeyboardInterrupt:  # user cancelled
            return False

    plugin.run_root = types.MethodType(run_root, plugin)


def get_registered(option_hooks=None, event_hooks=None,
                   command_hooks=None, root_access=None,
                   task_active=True):
    """ Returns a generator of registered plugins matching filters.

        `option_hooks`
            Boolean to include or exclude plugins using option hooks.
        `event_hooks`
            Boolean to include or exclude task event plugins.
        `command_hooks`
            Boolean to include or exclude command plugins.
        `root_access`
            Boolean to include or exclude root plugins.
        `task_active`
            Set to ``False`` to not filter by task-based plugins.

        Returns list of ``Plugin`` instances.
        """

    plugins = []

    for _, item in _registered:
        plugin, type_info = item

        # filter out any task-specific plugins
        if task_active:
            if type_info.get('disabled'):
                continue
        else:
            if plugin.options or plugin.task_only:
                continue

        if not option_hooks is None:
            if option_hooks != bool(type_info.get('option')):
                continue

        if not event_hooks is None:
            if event_hooks != bool(type_info.get('event')):
                continue

        if not command_hooks is None:
            if command_hooks != bool(type_info.get('command')):
                continue

        if not root_access is None:
            if root_access != plugin.needs_root:
                continue

        plugins.append(plugin)

    return plugins


def get_command_hook(command, task_active=True):
    """ Gets registered command ``Plugin`` instance for the provided
        command.

        `command`
            Command string registered to a plugin.
        `task_active`
            Set to ``False`` to indicate no active tasks.

        Returns ``Plugin`` instance or ``None``.
        """

    plugin_obj = _command_hooks.get(command)

    if plugin_obj:
        if task_active or (not plugin_obj.options and
                           not plugin_obj.task_only):

            if not _is_plugin_disabled(plugin_obj):
                return plugin_obj

    return None


def run_event_hooks(event, task):
    """ Executes registered task event plugins for the provided event and task.

        `event`
            Name of the event to trigger for the plugin:
                ('task_start', 'task_run', 'task_end')
        `task`
            ``Task`` instance.
        """

    # get chain of classes registered for this event
    call_chain = _event_hooks.get(event)

    if call_chain:
        # lookup the associated class method for this event
        event_methods = {
            'task_start': 'on_taskstart',
            'task_run': 'on_taskrun',
            'task_end': 'on_taskend'
        }
        method = event_methods.get(event)

        if method:
            for _, get_plugin in call_chain:
                plugin_obj = get_plugin()

                if not _is_plugin_disabled(plugin_obj):
                    try:
                        getattr(plugin_obj, method)(task)  # execute
                    except Exception:
                        # TODO: log these issues for plugin author or user
                        pass


def run_option_hooks(parser, disable_missing=True):
    """ Executes registered plugins using option hooks for the provided
        ``SettingParser`` instance.

        `parser`
            ``SettingParser`` instance.
        `disable_missing`
            Set to ``True`` to disable any plugins using option hooks whose
            defined option hooks are not available in the data returned from
            the parser.

        * Raises ``InvalidTaskConfig`` if task config parsing failed.
        """

    plugins = []
    state = {}  # state information

    def _raise_error(msg, block):
        """ Raises ``InvalidTaskConfig`` exception with given message.
            """
        if block:
            msg += u' (block: "{0}")'.format(block)

        raise errors.InvalidTaskConfig(parser.filename, reason=msg)

    def _run_hooks(options, block):
        """ Runs option hooks for the block and options provided.
            """

        for option, value_list in options:
            key = '{0}_{1}'.format(block, option) if block else option
            item = _option_hooks.get(key)

            if item:
                plugin_obj, props = item

                # enforce some properties
                if not key in state:
                    state[key] = 0
                state[key] += 1

                # currently only supports 'allow_duplicates'
                if not props.get('allow_duplicates', True) and state[key] > 1:
                    msg = u'Duplicate option "{0}"'.format(option)
                    _raise_error(msg, block)

                try:
                    plugin_obj.parse_option(option, block, *value_list)
                    plugins.append(plugin_obj)

                except TypeError:  # invalid value length
                    msg = u'Value mismatch for option "{0}"'.format(option)
                    _raise_error(msg, block)

                except ValueError as exc:
                    msg = unicode(exc)
                    if not msg:
                        msg = (u'Invalid value provided for option "{0}"'
                               .format(option))

                    _raise_error(msg, block)

            else:  # invalid key found
                msg = u'Invalid option "{0}" found'.format(option)
                _raise_error(msg, block)

    # run hooks for non-block options
    _run_hooks(parser.options, None)

    # run hooks for blocks
    for block, option_list in parser.blocks:
        _run_hooks(option_list, block)

    # disable any plugins using option hooks that didn't match parser data
    if disable_missing:
        reg_plgs = get_registered(option_hooks=True)

        for plugin in [p for p in reg_plgs if p not in plugins]:
            disable_plugin_instance(plugin)
