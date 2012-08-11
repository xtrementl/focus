""" This module provides the task-management command plugins that allow for
    starting, stopping, adding, removing, and modifying tasks from the
    command-line.
    """

import os
import tempfile
import subprocess

from focus import errors, parser, common
from focus.plugin import base, registration


__all__ = ('TaskStart', 'TaskStop', 'TaskCreate', 'TaskEdit',
           'TaskRemove', 'TaskRename', 'TaskList', 'TaskView')


def _print_tasks(env, tasks, mark_active=False):
    """ Prints task information using io stream.

        `env`
            ``Environment`` object.
        `tasks`
            List of tuples (task_name, options, block_options).
        `mark_active`
            Set to ``True`` to mark active task.
        """

    if env.task.active and mark_active:
        active_task = env.task.name
    else:
        active_task = None

    for task, options, blocks in tasks:
        # print heading
        invalid = False

        if task == active_task:
            method = 'success'
        else:
            if options is None and blocks is None:
                method = 'error'
                invalid = True

            else:
                method = 'write'

        opts = list(options or [])
        blks = list(blocks or [])

        write = getattr(env.io, method)
        write('~' * 80)
        write(' ' + task)
        write('~' * 80)
        env.io.write('')

        # non-block options
        if opts:
            for opt, values in opts:
                env.io.write('    {0}: {1}'.format(opt,
                             ', '.join(str(v) for v in values)))
            env.io.write('')

        # block options
        if blks:
            had_options = False

            for block, options in blks:
                if options:
                    had_options = True
                    env.io.write('    {{ {0} }}'.format(block))

                    for opt, values in options:
                        env.io.write('        {0}: {1}'.format(opt,
                                     ', '.join(str(v) for v in values)))
                    env.io.write('')

            if not had_options:
                blks = None

        if not opts and not blks:
            if invalid:
                env.io.write('  Invalid task.')
            else:
                env.io.write('  Empty task.')
            env.io.write('')


def _edit_task_config(env, task_config, confirm):
    """ Launches text editor to edit provided task configuration file.

        `env`
            Runtime ``Environment`` instance.
        `task_config`
            Path to task configuration file.

        `confirm`
            If task config is invalid after edit, prompt to re-edit.

        Return boolean.

        * Raises ``InvalidTaskConfig`` if edited task config fails to parse
          and `confirm` is ``False``.
        """

    # get editor program
    if common.IS_MACOSX:
        def_editor = 'open'
    else:
        def_editor = 'vi'
    editor = os.environ.get('EDITOR', def_editor)

    def _edit_file(filename):
        """ Launches editor for given filename.
            """
        proc = subprocess.Popen('{0} {1}'.format(editor, filename),
                                shell=True)
        proc.communicate()
        if proc.returncode == 0:
            try:
                # parse temp configuration file
                parser_ = parser.parse_config(filename, 'task')
                registration.run_option_hooks(parser_,
                                              disable_missing=False)

            except (parser.ParseError, errors.InvalidTaskConfig) as exc:
                reason = unicode(getattr(exc, 'reason', exc))
                raise errors.InvalidTaskConfig(task_config, reason=reason)

            return True
        else:
            return False

    try:
        # create temp copy of task config
        fd, tmpname = tempfile.mkstemp(suffix='.cfg', prefix='focus_')
        with open(task_config, 'r') as file_:
            os.write(fd, file_.read())
            os.close(fd)

        while True:
            try:
                # launch editor
                if not _edit_file(tmpname):
                    return False

                # overwrite original with temp
                with open(tmpname, 'r') as temp:
                    with open(task_config, 'w', 0) as config:
                        config.write(temp.read())

                return True

            except errors.InvalidTaskConfig as exc:
                if not confirm:
                    raise  # reraise

                # prompt to re-edit
                env.io.error(unicode(exc))
                while True:
                    try:
                        resp = env.io.prompt('Would you like to retry? (y/n) ')
                        resp = resp.strip().lower()
                    except KeyboardInterrupt:
                        return True

                    if resp == 'y':
                        break
                    elif resp == 'n':
                        return True

    except OSError:
        return False
    finally:
        common.safe_remove_file(tmpname)  # cleanup temp


class TaskStart(base.Plugin):
    """ Starts an existing task.
        """
    name = 'TaskStart'
    version = '0.1'
    target_version = '>=0.1'
    command = 'on'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('task_name')

    def execute(self, env, args):
        """ Starts a new task.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        # start the task
        if env.task.start(args.task_name):
            env.io.success(u'Task Loaded.')


class TaskStop(base.Plugin):
    """ Ends the active task.
        """
    name = 'TaskStop'
    version = '0.1'
    target_version = '>=0.1'
    command = 'end'
    task_only = True

    def execute(self, env, args):
        """ Stops the current task.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        env.task.stop()


class TaskCreate(base.Plugin):
    """ Creates a new task.
        """
    name = 'TaskCreate'
    version = '0.1'
    target_version = '>=0.1'
    command = 'make'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('task_name', help='task to create')
        parser.add_argument('clone_task', nargs='?',
                            help='existing task to clone')
        parser.add_argument('--skip-edit', action='store_true',
                            help='skip editing of task configuration')

    def execute(self, env, args):
        """ Creates a new task.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        task_name = args.task_name
        clone_task = args.clone_task

        if not env.task.create(task_name, clone_task):
            raise errors.FocusError(u'Could not create task "{0}"'
                                    .format(task_name))

        # open in task config in editor
        if not args.skip_edit:
            task_config = env.task.get_config_path(task_name)

            if not _edit_task_config(env, task_config, confirm=True):
                raise errors.FocusError(u'Could not open task config: {0}'
                                        .format(task_config))


class TaskEdit(base.Plugin):
    """ Edits configuration for an existing task.
        """
    name = 'TaskEdit'
    version = '0.1'
    target_version = '>=0.1'
    command = 'alter'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('task_name')

    def execute(self, env, args):
        """ Edits task configuration.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        task_name = args.task_name

        if not env.task.exists(task_name):
            raise errors.TaskNotFound(task_name)

        if env.task.active and task_name == env.task.name:
            raise errors.ActiveTask

        # open in task config in editor
        task_config = env.task.get_config_path(task_name)

        if not _edit_task_config(env, task_config, confirm=True):
            raise errors.FocusError(u'Could not open task config: {0}'
                                    .format(task_config))


class TaskRename(base.Plugin):
    """ Renames an existing task.
        """
    name = 'TaskRename'
    version = '0.1'
    target_version = '>=0.1'
    command = 'rename'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('old_task_name')
        parser.add_argument('new_task_name')

    def execute(self, env, args):
        """ Removes a task.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        # extract args
        old_task_name = args.old_task_name
        new_task_name = args.new_task_name

        if old_task_name == new_task_name:
            raise errors.FocusError(u'Could not rename task to itself')

        if env.task.active and env.task.name == old_task_name:
            raise errors.ActiveTask

        env.task.rename(old_task_name, new_task_name)


class TaskRemove(base.Plugin):
    """ Deletes an existing task.
        """
    name = 'TaskRemove'
    version = '0.1'
    target_version = '>=0.1'
    command = 'destroy'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('-f', '--force', action='store_true',
                            help='skip confirmation')
        parser.add_argument('task_name')

    def execute(self, env, args):
        """ Removes a task.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        # extract args
        task_name = args.task_name
        force = args.force

        if env.task.active and env.task.name == task_name:
            raise errors.ActiveTask

        if not env.task.exists(task_name):
            raise errors.TaskNotFound(task_name)

        if force:
            env.task.remove(task_name)

        else:
            try:
                while True:
                    prompt = ('Are you sure you want to delete "{0}" (y/n)? '
                              .format(task_name))
                    resp = env.io.prompt(prompt, newline=False).lower()

                    if resp in ('y', 'n'):
                        if resp == 'y':
                            env.task.remove(task_name)
                        break

            except KeyboardInterrupt:
                pass


class TaskList(base.Plugin):
    """ Lists all available tasks and related information.
        """
    name = 'TaskList'
    version = '0.1'
    target_version = '>=0.1'
    command = 'list'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('-v', '--verbose',
                            action='store_true',
                            help='show extended task info')

    def execute(self, env, args):
        """ Lists all valid tasks.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        tasks = env.task.get_list_info()
        if not tasks:
            env.io.write("No tasks found.")

        else:
            if args.verbose:
                _print_tasks(env, tasks, mark_active=True)

            else:
                if env.task.active:
                    active_task = env.task.name
                else:
                    active_task = None

                for task, options, blocks in tasks:
                    if task == active_task:
                        env.io.success(task + ' *')
                    else:
                        if options is None and blocks is None:
                            env.io.error(task + ' ~')
                        else:
                            env.io.write(task)


class TaskView(base.Plugin):
    """ Shows information for an existing task.
        """
    name = 'TaskView'
    version = '0.1'
    target_version = '>=0.1'
    command = 'view'

    def setup_parser(self, parser):
        """ Setup the argument parser.

            `parser`
                ``FocusArgParser`` object.
            """

        parser.add_argument('task_name', nargs='?',
                            help='if not provided, views active task')

    def execute(self, env, args):
        """ Prints task information.

            `env`
                Runtime ``Environment`` instance.
            `args`
                Arguments object from arg parser.
            """

        task_name = args.task_name

        if task_name is None:
            if not env.task.active:
                raise errors.NoActiveTask
            task_name = env.task.name

        tasks = env.task.get_list_info(task_name)
        if not tasks:
            raise errors.TaskNotFound(task_name)

        _print_tasks(env, tasks)
