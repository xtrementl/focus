Introduction
============

Focus is a command-line productivity tool for improved task workflows.

Why Focus?
----------

For developers, Focus aims to help fight distractions while you work;
less distractions means more focus. Currently, Focus targets Unix-like
operating systems, such as Linux or Mac OSX.

Features
========

Open Applications
-----------------
Launch applications needed for your task.

Close Applications
------------------
Quit unnecessary applications when starting your task.

Block Applications
------------------
Continuously quit unnecessary applications if they are launched during a task.

Block Websites
--------------
Block distracting websites, such as Hacker News, Facebook, YouTube, and
Twitter.

Run Commands
------------
Execute arbitrary shell commands useful for your task.

Play Sounds
-----------
Play a sound after your task timer runs out or whenever you end the task.
You can also play a sound when starting tasks, in case you want to get
your groove on.

Notifications
-------------
Show a popup system notification message when a task is started or
has ended, either by you completing the task or the timer running out.

Update IM Status
----------------
Update the account status for your favorite instant messenger (IM) applications
while you work. Focus supports `Pidgin <http://www.pidgin.im/>`_,
`Empathy <https://live.gnome.org/Empathy>`_, and
`Skype <http://www.skype.com>`_ on Linux and `Adium <http://adium.im/>`_ and
`Skype <http://www.skype.com>`_ on Mac OSX.

Track Your Time
---------------
Keep tabs on how long you work on tasks per day. Focus will record your time
automatically and present your time as a simple report.

**If these features won't do it for you, Focus boasts a simple, yet powerful
plugin system. More on this later.**

Installation
============

    $ sudo pip install focus

or from source:

    $ sudo python setup.py install

Python Libraries
----------------

The following Python libraries are required to run Focus; though ``pip``
should handle taking care of installing them if not available.

* psutil >= 0.4.1
* argparse (Python <2.7)
* dbus (Linux only)

Optional External Dependencies
------------------------------

* Linux:
    `mpg123 <http://www.mpg123.de/>`_, `play <http://sox.sourceforge.net/>`_,
    or `aplay <http://www.alsaplayer.org/>`_ [WAV only] (to play sounds)

* Mac OSX:
    `terminal-notifier <https://github.com/alloy/terminal-notifier>`_
    or `growlnotify <http://growl.info/extras.php/#growlnotify>`_
    (to show notifications)

Usage
=====

Create Task
-----------

    $ focus make task_name [--skip-edit]

or, clone from existing task:

    $ focus make task_name other_task [--skip-edit]

This command opens the task configuration file using the shell's default editor
($EDITOR), unless the ``--skip-edit`` flag is provided. After the editor exits,
the configuration file is validated and will prompt for retry if validation
fails.

Start Task
----------

    $ focus on task_name

This starts the provided task, running any initial settings as indicated in the
task's configuration file.

End Task
--------

    $ focus end

This ends the current task, running any ending settings as indicated in the
task's configuration file.

*Note: this command is only available when a task is active.*

Edit Task
---------

    $ focus edit task_name [--skip-edit]

Like the ``make`` command, this command opens the task configuration file using
the shell's default editor ($EDITOR). After the editor exits, the
configuration file is validated and will prompt for retry if validation fails.

List Tasks
----------

    $ focus list [-v] [--verbose]

This will scan for existing tasks with valid configuration files and print
the names of the tasks found. Specify the ``-v`` or ``--verbose`` flag to also
print setting information for each task's configuration file. Invalid tasks
are marked in red, while the active task is marked in green.

View Task
---------

    $ focus view [task_name]

This prints the setting information from the task's configuration file.
If no task name is provided, the active task will be shown.

Rename Task
-----------

    $ focus rename old_task_name new_task_name

This commands gives the provided task a new name.

Delete Task
-----------

    $ focus destroy task_name [-f] [--force]

This commands removes the provided task after prompting for confirmation.
Specify the ``-f`` or ``--force`` flag to skip confirmation.

Show Remaining Time for Active Task
-----------------------------------

    $ focus left [-s] [--short]

This commands prints the amount of time remaining, in minutes, for the active
task. Specify the ``-s`` or ``--short`` flag to print just the number of
minutes.

*Note: this command is only available if the active task has defined the
duration option.*

Show Available Usage Statistics
-------------------------------

    $ focus stat [start]

This commands prints the daily task usage summaries, broken out per task, for
every day from the starting period through the current day.

The starting period supports the following values ::

    today, t
    yesterday, y
    {n}d, {n}day, {n} day, {n}days, {n} days, {n} day ago, {n} days ago
    w, wk, week, last week
    {n}w, {n}wk, {n}week, {n}weeks, {n} week ago, {n} weeks ago

where {n} is replaced with a number (e.g. ``1d`` for 1 day ago to today).
If no starting period is provided, then ``today`` will be used.

Task Configuration
==================

Each task is described by its associated configuration file. When a new task
is created, the `default task configuration file
<https://github.com/xtrementl/focus/blob/master/conf/focus_task.cfg>`_ will be
used.

The task configuration file is composed of a number of either non-block or
block options. Each value for an option may be quoted with either single or
double quote, or may be unquoted if spaces and quotes are escaped.

**Examples:** ::

    # option => value 1, value2, value 3, value 4, value\ 5
    option "value 1", value2, 'value 3', value\ 4, value\\ 5;

    # option => a 'b', a 'b', a \ b, a \ b, a \ b, a \\ b, 'abc' - "d"
    option 'a \'b\'', a\ \'b\', "a \\ b", "a \ b",
            a\ \\ b, a\ \\\ b, "'abc' - \"d\"";

Applications
------------

The ``apps`` block allows for options to run, close, or block applications.
Each option supports multiple values and can be repeated as multiple option
definitions.

The ``run`` option supports an arbitrary shell command, an application name, or
the path to an executable script. Arguments and shell redirection are also
possible. This option will be initiated when starting a task.

The ``close`` option supports an arbitrary shell command, an application name,
or the path to an executable script. Unlike ``run``, shell redirection is not
supported and all arguments provided are considered as part of the
command/application name provided (e.g. "Google Chrome" not "Google" with
"Chrome" argument). This option will be initiated when starting on a task.

The ``block`` option behaves exactly like ``close``, except that it runs
continously while the task is active (approximately once a second).

The ``run`` and ``close`` options also support the "end_" prefix which will
instead be activated when a task is manually ended.

For example: ::

    apps {
        run /path/to/file;       # run app at task start
        close /path/to/file;     # close app at task start
        end_run /path/to/file;   # run app at task end (manual)
        end_close /path/to/file; # close app at task end (manual)

        # See Task Timer below..
        timer_run /path/to/file;   # run app at task end (timer elapsed)
        timer_close /path/to/file; # close app at task end (timer elapsed)
    }

Task Timer
----------

The ``duration`` option will automatically end the task after the specified
number of minutes. This option supports only a single value > 0 and the
option cannot be defined more than once.

This also enables the ``left`` command when running the ``focus`` program to
view remaining task time.

Additionally, any options that support the "end_" prefix will also support
the "timer_" prefix. They function similar to "end_" prefixed options, except
they are only activated after the task timer has elapsed.

For example: ::

    apps {
        timer_run /path/to/file;   # run app at task end (timer elapsed)
        timer_close /path/to/file; # close app at task end (timer elapsed)
    }

Blocking Websites
-----------------

The ``block`` option under the ``sites`` block allows for blocking website
domains while the task is active. Each option supports one or more domain
values. The option may be redefined multiple times.

For example: ::

    sites {
        block google.com, twitter.com;
        block youtube.com, "othersite.com";
    }

Under the hood, Focus updates the system HOSTS file (/etc/hosts) with mappings
of the provided domains to the local machine. Because of this, you will have to
provide an entry for each relevant subdomain as well if necessary. As a result,
this strategy won't scale when blocking a site with numerous subdomains.
Perhaps, another solution like a local DNS server would be more appropriate
(e.g. `dnsmasq <http://www.thekelleys.org.uk/dnsmasq/doc.html>`_).

As a convenience, any domains configured will also map the following
subdomains: ``m``, ``www``, ``mobile``.

For example::

    google.com => google.com, www.google.com, m.google.com, mobile.google.com

Playing Sounds
--------------

The ``play`` options for the ``sounds`` block support the path to a sound file
that is playable on your system via available external binaries (``mpg123``,
``play``, and ``aplay`` [WAV only]). Only a single value is supported for each
option, and each type of option cannot be defined more than once. Make sure
your preferred binary is installed and works correctly by manually running your
sound file through the program.

For example: ::

    sounds {
        play /path/to/file;        # play sound file at task start
        end_play /path/to/file;    # play sound file at task end (manual)
        timer_play /path/to/file;  # play sound file at task end (timer elapsed)
    }

Notifications
-------------

The ``show`` options for the ``notify`` block support a single message that
will be shown as a system notification. Only a single value is supported for
each option, and each type of option cannot be defined more than once.

On Linux/Unix, the feature functions via the DBUS IPC bus. On Mac OSX, external
binaries (``terminal-notifier`` and ``growlnotify``) will be used when
available; otherwise, a fallback alert dialog will be shown. If using Mac OSX,
make sure your preferred binary is installed and works correctly, unless the
fallback method is desired.

For example: ::

    notify {
        show "message here";        # notify at task start
        end_show "message here";    # notify at task end (manual)
        timer_show "message here";  # notify at task end (timer elapsed)
    }

Updating IM Status
------------------

The ``im`` block allows for options to update the status information for
a number of running instant messenger applications.

The ``status_msg`` option supports defining a name that can be referenced when
specifying the ``status``, ``end_status`` and ``timer_status`` options. The
option takes two arguments: the first being the identifier name, and the second,
the value for the status message. The option can be defined more than once to
define multiple status messages to use.

For example: ::

    im {
        status_msg message_name, value;
        status_msg brb, brb;
        status_msg brb2, be\ right\ back;
        status_msg omg, "oh em gee";
        status_msg working, "definitely busy here..";
    }

The ``status`` option is activated at the start of a task, and it accepts
either the new status, or both the new status and new status message as
arguments.

For the status argument, the following values are available: ::

    'online'    - Online/Available
    'away'      - Away
    'long_away' - Extended Away
    'busy'      - Busy
    'hidden'    - Hidden/Invisible

For the optional message argument, a string value may be provided. To reference
an existing ``status_msg`` option definition, simply provide the ``status_msg``
name prefixed with ":" (e.g. :working, :brb, :omg). The ``status`` option also
supports the "end_" and "timer_" prefixes which will instead be activated when
a task is manually ended or after the timer elapses, respectively.

For example: ::

    im {
        status_msg working, "definitely busy here...";
        status busy, :working;       # change status at task start

        #status away;
        #status busy, really\ busy;
        #status busy, "don't bother";
        end_status online;          # change status at task end (manual)
        timer_status online;        # change status at task end (timer elapsed)

        status_msg play, "reading some twitters";
        #status away, :play;
    }

Plugin System
=============

Focus provides a simple and flexible plugin system to extend the core
functionality. In fact, plugins are used internally for everything.

Installing Plugins
------------------

After running the ``focus`` command, the ``.focus`` directory is created in
your home directory ($HOME or ~). Under that lives a ``plugins`` subdirectory,
where you can drop your .py python plugin files. If they are valid, the plugins
will automatically become available when running ``focus``. For command
plugins, running ``focus`` will print a help banner with the installed
commands, which will include your plugins.

*Remember, if the plugin is available only for active tasks, the appropriate
task must be active to see your plugin show up.*

Command Plugins
---------------

Command plugins define the commands that are available for the Focus binary
(e.g. ``on``, ``make``, etc.). These can be available always, only for tasks
that define certain options, or only for active tasks.

The ``command`` class attribute identifies the plugin as a command plugin and
specifies the actual command name to register with the plugin.

*Note: The command name should be unique.*

The plugin should define the ``execute()`` method for running the command. The
``env`` argument represents the environment and the ``args`` argument is the
result of parsing the command-line arguments using the ``ArgumentParser``
object.

**Method Definition:** ::

    def execute(self, env, args):
        env.io.write('Verbose: {0}'.format(args.verbose))

To simply print an error message, use the ``env.io.error()`` method. If you
need to also return a specific error code along with printing an error message
raise a ``FocusError`` exception from the ``focus.errors`` module: ::

    from focus.errors import FocusError

    def execute(self, env, args):
        # env.io.error('Oh noes!')  # just prints and returns exit code 0
        raise FocusError('message here', code=123)

If the plugin needs to define any command-line arguments, it should define the
``setup_parser()`` method. The ``parser`` argument is an instance of
``argparse.ArgumentParser`` and should be updated as necessary to add
arguments.

**Method Definition:** ::

    def setup_parser(self, parser):
        parser.add_argument('-v', '--verbose', action='store_true')

**Plugin Example:** ::

    from focus.plugin import Plugin

    class Foo(Plugin):
       """ Description of plugin, used when generating help message.
           """
       name = "FooPlugin"         # Name of plugin, must be unique
       version = "1.0"            # Plugin version
       target_version = ">=0.1"   # Target Focus version, (<, <=, ==, >=, >)
       command = "bar"            # Command name

       def setup_parser(self, parser):
           parser.add_argument('-v', '--verbose', action='store_true')

       def execute(self, env, args):
           env.io.write('Verbose: {0}'.format(args.verbose))
           #env.io.error('Oh noes!')
           #env.io.success('Woot')

           # resp = env.io.prompt('Are you distracted? (y/n)')
           # stdin_data = env.io.read()

Task Event Plugins
------------------

Task event plugins are only available for active tasks. They can be registered
to run at the start of the task, during the task loop (every second), at the
end of a task, or some combination therein. These plugins will be run within a
daemon process when the task starts.

The ``events`` class attribute identifies the plugin as a task event plugin and
specifies the events of the task that should be registered: ``task_start``,
``task_run``, ``task_end``.

The plugin should define the ``on_taskstart()``, ``on_taskrun()``, or
``on_taskend()`` methods corresponding to the values provided for the
``events`` attribute. The ``task`` argument represents the active task, which
includes ``name``, ``duration`` (minutes), and a few methods such as
``start()`` and ``stop()``.

**Method Definition:** ::

    def on_taskstart(self, task):
        pass

**Plugin Example:** ::

    from focus.plugin import Plugin

    class Foo(Plugin):
       """ Description of plugin.
           """
       name = "FooPlugin"         # Name of plugin, must be unique
       version = "1.0"            # Plugin version
       target_version = ">=0.1"   # Target Focus version, (<, <=, ==, >=, >)
       events = ['task_start', 'task_run', 'task_end']

       def on_taskstart(self, task):
           pass

       def on_taskrun(self, task):
           pass

       def on_taskend(self, task):
           pass

Plugin Options
--------------

Two attributes exist to allow plugins to only be loaded for active tasks:

1. **options**

   Set the ``options`` class attribute. This defines the options that, if
   provided in a task configuration file, will trigger the load of this plugin.
   Options are either non-block (e.g. ``duration``) or block
   (e.g. ``apps`` => { ``run``, ``close``, ``block`` }, ``sites`` =>
   { ``block`` }, etc.). When this attribute is set, the plugin should define
   the ``parse_option()`` method in order to parse the values set in a task
   configuration file. See example below.

   *Note: these options should be unique.*

   **Plugin Snippet:** ::

       from focus.plugin import Plugin

       class Foo(Plugin):
           ...
           options = [
               # duration (non-block option)
               {
                   'name': 'duration',
                   'allow_duplicates': False  # disallow duplicate definitions
               },

               # apps.run, apps.close (block options)
               {
                   'block': 'apps',
                   'options': [
                       {
                           'name': 'run',
                           'allow_duplicates': True  # the default
                       },
                       { 'name': 'close' }
                   ]
               }
           ]

   **Task Configuration Example:** ::

       task {
           duration 30;

           apps {
               run firefox, chromium, /path/to/file, /path/to/other\ file;
               run "/path/to/file arg1 arg2", helloworld\ -a\ b;
               close adium;
           }
       }

   **Method Definition:** ::

       def parse_option(self, option, block_name, *values):
           # raise ValueError exception with a message to reject the provided
           # value. this will propagate up to the cli when loading a task

   Here, the ``option`` and ``block_name`` names for the currently parsed
   option are provided. ``block_name`` will be ``None`` when parsing non-block
   options. ``values`` holds one or more values associated with the provided
   option.

2. **task_only**

   Set the ``task_only`` class attribute, so the plugin will be available for
   any task once started.

   **Plugin Snippet:** ::

       class Foo(Plugin):
           ...
           task_only = True
           ...

Root Access
-----------

If a plugin needs root access, it should define the ``needs_root`` attribute.
When set, this installs a ``run_root()`` method on the plugin class, which
accepts an arbitrary command string and returns a boolean for success or
failure. Internally, Focus uses the ``sudo`` command to temporarily escalate
privileges.

**Plugin Snippet:** ::

    from focus.plugin import Plugin

    class Foo(Plugin):
        ...
        command = 'foo'
        events = ['task_start']
        needs_root = True
        
        def execute(self, env, args):
            self.run_root('whoami >> /tmp/whoami_focus.log')

        def on_taskstart(self, task):
            self.run_root('whoami >> /tmp/whoami_focus2.log')
