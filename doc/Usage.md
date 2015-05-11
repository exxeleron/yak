## Usage

`yak` provides two operation modes:
* interactive shell,
* batch execution.

### Interactive mode

In interactive mode, execute `yak` in the command line:

```bash
$ yak
yak 3.0.0 [20140416120040] (c) 2011-2014 exxeleron

Type 'help' or '?' to list available commands.
>>>
```

### Batch operation mode

In batch operation mode, start `yak` with command and component/namespace/group id provided:

```bash
$ yak start kdb.rdb
```

### Commands

`yak` provides following commands:

| Command        | Shortcut | Description
|----------------|----------|---------------------------------------------------------
| `start`        |          | starts component(s) with given component id(s)
| `stop`         |          | stops component(s) with given component id(s)
| `interrupt`    |          | sends interrupt signal to component(s) with given component id(s) (UNIX only)
| `restart`      |          | restarts component(s) with given component id(s)
| `info`         |    .     | prints status information about listed component(s)
| `details`      |    :     | prints detailed information about listed component(s)
| `log/out/err`  |          | open component log file, standard output or standard error respectively in external pager
| `console`      |          | starts single component in interactive mode; logger is automatically reconfigured to CONSOLE; no readline support is provided
| `quit`         |    \\    | exits the command line tool
| `_show_options`|    %     | Shows configuration of the command line tool (i.e.: components configuration, status file location)
| `_show_order`  |    !     | Shows computed dependency order


All commands applies to one or more components. Components can be listed by: component ids (full name in format `namespace.id`), namespaces or groups. yak rearranges order of components to maintain required dependency order.

It's possible to use a negation symbol (`!`) to exclude some of the components from the list. For example:
```bash
>>> stop * !core.tick               # stops all components except of core.tick
>>> restart core !feed              # restarts all components in core group except ones defined in feed namespace
```


### Configurable options

In order to configure `yak` paths (log directories or system location) command line options can be used:

|  Parameter                                       | Default       | Description
|--------------------------------------------------|---------------|------------
| <pre>-c CONFIG</pre> <pre>--config=CONFIG</pre>  | 'system.cfg'  | location of the configuration file
| <pre>-s STATUS</pre> <pre>--status=STATUS</pre>  | 'yak.status'  | location of the status file
| <pre>-l LOG</pre> <pre>--log=LOG</pre>           | 'yak.log'     | location of the yak log file; date/time formats can be used in the file name (as described in `strftime(3)` manual)
| <pre>-v VIEWER</pre> <pre>--viewer=VIEWER</pre>  |               | external viewer/pager
| <pre>-d DELIM</pre> <pre>--delimiter=DELIM</pre> | padded spaces | delimiter for the info command
| <pre>-f FORMAT</pre> <pre>--format=FORMAT</pre>  | [see below]   | format for the info command
| <pre>-F STATUS</pre> <pre>--filter=STATUS</pre>  | empty         | filter info result by component status
| <pre>-A ALIAS</pre> <pre>--alias=ALIAS</pre>     |               | define command alias
| <pre>-a ARGS</pre> <pre>--arguments=ARGS</pre>   | empty         | additional arguments for the processes (valid for `start`, `restart` and `console` commands)


It is convenient to set `YAK_OPTS` environmental variable with default options for yak. Command line options always take precedence before `YAK_OPTS`. 

Example `YAK_OPTS` value:

```bash
$ echo $YAK_OPTS
-c /kdb/etc/system.cfg -s /kdb/data/yak/yak.status -l /kdb/log/yak/yak-%Y.%m.%d.log
```

### Component status

Each component inside yak is assigned with status attribute:

|  Status      | Description
|--------------|-------------------------------------------------------------------------------------------------------------------------------
| `RUNNING`    | Component has been started and there is an active OS process matching original PID.
| `DISTURBED`  | Component has been started, there is an active OS process matching original PID and file with STDERR redirection is non-empty.
| `STOPPED`    | Component has been stopped by the user or component hasn't been started yet.
| `TERMINATED` | OS process with matching original PID cannot be found and the component hasn't been stopped by the user.
| `WSFULL`     | q only. If file with STDERR redirection is non-empty and finishes with one of the following: wsfull or -w abort.


Output from the `info` command can be filtered based on component status via command line parameter `-F / --filter`.

```bash
yak info -F RUNNING#DISTURBED
```


### Command aliases

Command aliases allow user to chain multiple commands and bind these with a custom name. Alias is declared and defined via command line parameter `-A / --alias`.

For example: user can define a `restart_console` command, which stops and restarts a single component in the interactive console mode.

```bash
yak --alias restart_console "stop, console"
```

Define a `info_dt` alias, which only show information about components with status DISTURBED or TERMINATED:

```bash
yak --alias info_dt "info -F DISTURBED#TERMINATED"
```

For convenience, command aliases can be set via `YAK_OPTS` environmental variable. For example:
```bash
$ echo $YAK_OPTS
-c /kdb/etc/system.cfg -s /kdb/data/yak/yak.status -l /kdb/log/yak/yak-%Y.%m.%d.log -A restart_console "stop, console" -A restart_verify "stop, start, info"
```


### Formatting info output

This section describes how to customize output format for the info command using command line option `-f / --format`.

Format argument is list of `#` (`hash`) separated columns, where each column is described as:

```
column_id: [align]minimal_width.[maximal_width]
align:     < left-aligned, > right-aligned
```

Available columns:

```
cpuSys   cpuUser    executedCmd    memRss   memUsage   memVms       pid
port     started    startedBy      status   stopped    stoppedBy    uid
```

Default values are set to:

```
uid:18.18#pid:5#port:5#status:11#started:19#stopped:19
```

Sample output:
```
uid                pid   port   status      started             stopped
-----------------------------------------------------------------------------------
core.hdb           8364  15005  RUNNING     2014.05.16 09:41:50
core.monitor                    TERMINATED  2014.05.16 09:41:57
core.rdb           3904  -16000 RUNNING     2014.05.16 09:41:53
```

Top-like output can be achieved using format:

```
uid:18.18#pid:<5#port:6#status:11#cpuUser:>10.10#cpuSys:>10.10#cpuUsage:>6.6#memUsage:>6.6#memVms:>8.8#memRss:>8.8#memCap:>8
```

Sample output:
```
uid                pid   port   status      cpuUser    cpuSys     cpuUsa memUsa memVms   memRss   memCap
----------------------------------------------------------------------------------------------------------
core.hdb           8364  15005  RUNNING          0.016      0.016         0.058     2328     4780
core.monitor                    TERMINATED       0.000      0.000         0.000        0        0
core.rdb           3904  -16000 RUNNING          0.031      0.000         0.058     2328     4812
```

***Note:***

Please be aware that depending on the environment, special characters (`<`, `>` or `#`) may be expanded. For example, `bash` may expand `*` to current directory content. This can be prevented by simply enclosing whole parameters with double quotes. Therefore, the `.*` should be changed to `".*"` or `.\*`.
