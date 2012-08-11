""" This module provides the command-line interface plugin for the runtime
    environment.
    """

import re
import sys
import argparse

from focus.errors import HelpBanner
from focus.plugin import registration
from focus.version import __version__

__all__ = ('FocusArgParser', 'CLI')

# workaround for buggy python 2.6 deprecated warnings,
# this should be integrated into argparse module

if sys.version_info[:2] == (2, 6):
    import warnings
    warnings.filterwarnings(action='ignore',
                            message='BaseException.message has been deprecated'
                                    ' as of Python 2.6',
                            category=DeprecationWarning,
                            module='argparse')


class FocusArgParser(argparse.ArgumentParser):
    """ Subclass of ArgumentParser for specific features needed for output.
        """

    def exit(self, status=0, message=None):
        """ Handle general message exits (e.g. version).
            """
        if message:
            raise HelpBanner(message.strip(), code=status)

    def format_help(self):
        """ Strip out { } redundant subcommand section.
            """
        help_msg = super(FocusArgParser, self).format_help()
        return re.sub(r'\{.+\}', '', help_msg)

    def error(self, message):
        """ Raise to print help banner.
            """
        raise HelpBanner(self.format_help())

    def print_help(self, file=None):
        """ Raise to print help banner.
            """
        raise HelpBanner(self.format_help())


class CLI(object):
    """ Command-line interface. Provides the main framework that
        executes all commands for the main program.
        """

    def _handle_help(self, env, args):
        """ Handles showing help information for arguments provided.

            `env`
                Runtime ``Environment`` instance.
            `args`
                List of argument strings passed.

            Returns ``False`` if nothing handled.

            * Raises ``HelpBanner`` exception if valid subcommand provided.
            """

        if args:
            # command help (focus help [command])
            # get command plugin registered for command
            active = env.task.active
            plugin_obj = registration.get_command_hook(args[0], active)

            if plugin_obj:
                parser = self._get_plugin_parser(plugin_obj)
                raise HelpBanner(parser.format_help(), code=0)

        return False

    def _handle_command(self, command, env, args):
        """ Handles calling appropriate command plugin based on the arguments
            provided.

            `command`
                Command string.
            `env`
                Runtime ``Environment`` instance.
            `args`
                List of argument strings passed.

            Returns ``False`` if nothing handled.

            * Raises ``HelpBanner`` exception if mismatched command arguments.
            """
        # get command plugin registered for command
        # note, we're guaranteed to have a command string by this point
        plugin_obj = registration.get_command_hook(command, env.task.active)

        # check if plugin is task-specific or has option hooks implying
        # task-specific behavior
        if plugin_obj and not env.task.active:
            if plugin_obj.task_only or plugin_obj.options:
                plugin_obj = None

        if plugin_obj:
            # plugin needs root, setup root access via sudo
            if plugin_obj.needs_root:
                registration.setup_sudo_access(plugin_obj)

            # parse arguments
            parser = self._get_plugin_parser(plugin_obj)
            parsed_args = parser.parse_args(args)

            # run plugin
            plugin_obj.execute(env, parsed_args)
            return True

        return False

    def _get_parser(self, env):
        """ Creates base argument parser.

            `env`
                Runtime ``Environment`` instance.

            * Raises ``HelpBanner`` exception when certain conditions apply.

            Returns ``FocusArgumentParser`` object.
            """

        version_str = 'focus version ' + __version__
        usage_str = 'focus [-h] [-v] [--no-color] <command> [<args>]'

        # setup parser
        parser = FocusArgParser(description=("Command-line productivity tool "
                                             "for improved task workflows."),
                                epilog=("See 'focus help <command>' for more "
                                        "information on a specific command."),
                                usage=usage_str)

        parser.add_argument('-v', '--version', action='version',
                            version=version_str)
        parser.add_argument('--no-color', action='store_true',
                            help='disables colors')

        # fetch command plugins
        commands = []
        active = env.task.active
        command_hooks = registration.get_registered(command_hooks=True,
                                                    task_active=active)

        # extract command name and docstrings as help text
        for plugin in command_hooks:
            help_text = (plugin.__doc__ or '').strip().rstrip('.').lower()
            commands.append((plugin.command, help_text))
        commands.sort(key=lambda x: x[0])  # command ordered

        # install subparsers
        subparsers = parser.add_subparsers(title='available commands')

        # install 'help' subparser
        help_parser = subparsers.add_parser('help', add_help=False)
        help_parser.set_defaults(func=self._handle_help)

        # install 'version' subparser
        version_parser = subparsers.add_parser('version', add_help=False)

        def _print_version(env, args):
            env.io.write(version_str)
            return True
        version_parser.set_defaults(func=_print_version)

        # install command subparsers based on registered command plugins.
        # this allows for focus commands (e.g. focus on [...])

        for command, help_ in commands:
            cmd_parser = subparsers.add_parser(command, help=help_,
                                               add_help=False)

            # use wrapper to bind command value and passthru to _handle_command
            # when executed later
            def _run(command):
                def _wrapper(env, args):
                    return self._handle_command(command, env, args)
                return _wrapper
            cmd_parser.set_defaults(func=_run(command))

        return parser

    def _get_plugin_parser(self, plugin_obj):
        """ Creates a plugin argument parser.

            `plugin_obj`
                ``Plugin`` object.

            Returns ``FocusArgParser`` object.
            """

        prog_name = 'focus ' + plugin_obj.command
        desc = (plugin_obj.__doc__ or '').strip()

        parser = FocusArgParser(prog=prog_name, description=desc)
        plugin_obj.setup_parser(parser)

        return parser

    def execute(self, env):
        """ Executes basic flags and command plugins.

            `env`
                Runtime ``Environment`` instance.

            * Raises ``FocusError`` exception when certain conditions apply.
            """

        # parse args
        parser = self._get_parser(env)
        parsed_args, cmd_args = parser.parse_known_args(env.args)

        # disable colors
        if parsed_args.no_color:
            env.io.set_colored(False)

        # run command handler passing any remaining args
        if not parsed_args.func(env, cmd_args):
            raise HelpBanner(parser.format_help())
