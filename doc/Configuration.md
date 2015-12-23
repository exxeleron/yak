## Configuration

`yak` process management tool reads one configuration file: `system.cfg`. Detailed format description can be found in Enterprise Components 3.0 Developers' Documentation.

***Note:***
In order to avoid unexpected behaviour, single configuration file has to be used in conjunction with the same status file.

Top-level elements of `system.cfg` are groups. Each group wraps some number of components instances. Instance names are built from namespace identifier and instance id. Configured components can be later referred using group name, namespace, or full instance name.

Example group configuration:

```ini
[[group:emea]]
  [[input.feedEmea]]
  ...
  [[input.tickEmea]]
  ...
  [[core.rdbEmea]]
  ...
[[group:asia]]
  [[input.feedAsia]]
  ...
  [[input.tickAsia]]
  ...
  [[core.rdbAsia]]
  ...
```

And some sample `yak` commands with different contexts used:

```bash
$ yak start emea          # Start 'emea' group only
$ yak start asia          # Start 'asia' group only
$ yak stop core.tickEmea  # Start 'core.tickEmea' only
$ yak restart input       # Restart all instances in 'input' namespace (all groups)
$ yak stop '*'            # Stop everything (every instance in all groups)
```

### Component types

Each component has to define a type fields containing one of following types:

- generic command-line component (`cmd`)
- q component (`q`) – q based process, deployed instance of component
- batch component (`b`) – batch job 
- external component (`c`) – these components are just for information purposes – `yak` does not support any actions for them

Type definition has to be followed by a colon and a component type. Component type is process specific and is required for the configuration of `q` processes.

#### Configuration parameters – generic component (runs any command)

Parameter | Description
:-------------- | :----------
`requires` | list of required component ids command
`command` | command to be executed
`type` | here: always cmd
`cpuAffinity` | list of cores for affinity configuration
`startWait` | period to wait for component startup
`stopWait` | period to wait for component stop
`binPath` | working directory
`dataPath` | data directory
`logPath` | directory for standard output and standard error redirections
`timestampMode` | defines whether timestamping while performing start/stop commands occurs in UTC or local time. valid options: `utc`, `local`


#### Configuration parameters – q component

In addition to parameters defined for generic component, following parameters can be defined for `q`/`kdb+`-based component(s):

Parameter | Description
----------------|------------
`requires` | list of required component ids
`command` | command to be executed
`type` | here: always q
`cpuAffinity` | list of cores for affinity configuration
`startWait` | period to wait for component startup
`stopWait` | period to wait for component stop
`port` | port to use
`libs` | list of additional libraries to be load on start up
`mulithreaded` | multithreaded input queue mode for q process (negative port value)
`uOpt` | authorization file mode for q process (u/U options))
`uFile` | authorization file for q process
`binPath` | working directory
`dataPath` | data directory
`logPath` | directory for standard output and standard error redirections
`qPath` | location of the q interpreter (used to determinate between multiple q environments)
`qHome` | location of the QHOME (used to determinate between multiple q environments)


### Environmental variables

`yak` adds a number of environmental variables to the process environment. List of such variables is defined in `system.cfg`:

```ini
eventDest = LOG, MONITOR
eventMemHistSize = 10000
eventPath = /data/shared/events/

etcPath = $BIN_ROOT/etc_shared/, /app/etc/$EC_COMPONENT
libPath = /q/lib, $BIN_ROOT/bin/$EC_COMPONENT

export = etcPath, libPath, eventDest, eventPath, eventMemHistSize
```

Variable names are converted to UPPPER_UNDERSCORE_CONVENTION and prefixed with `EC_` prefix, e.g.: `libPath` is exported as `EC_LIB_PATH`.
Configuration entry as above would make `yak` add all global variables listed in the `export` key to the execution environment (for newly created processes). 

Note: `EC_COMPONENT_ID`, `EC_COMPONENT`, `EC_GROUP`, `EC_COMPONENT_PKG`, `EC_COMPONENT_TYPE`, `EC_COMPONENT_INSTANCE` are exported implicitly for each managed process.

While starting a component, `yak` saves all the environmental variables in the file: `[COMPONENT_ID]_[TIMESTAMP].stdenv` located in the directory configured via `logPath` key in the configuration.

### Sample configuration file (without global variables definitions)

```ini
basePort = 14000

Q32_HOME = /opt/q32/
Q32_PATH = /opt/q32/l32

[group:core]                          # group declaration
  cpuAffinity = 0, 1
  startWait = 3 

  [[core.hdb]]                        # definition of process hdb in namespace kdb
  type = q:hdb/hdb                    # type of process:component package/schema file
  port = $basePort + 10               # port definition
  command = "q hdb.q"

  [[core.rdb]]
  type = q:rdb/rdb
  requires = core.hdb                 # use process name with namespace here
  port = 16000                        # explicit port definition
  command = "q rdb.q"

  [[core.monitor]]                    # sample non-q component definition
  type = cmd:python                   # type of process (part after : is ignored)
  requires = core.hdb, core.rdb
  command = "python monitor.py"

[group:stream]
  # define u/U options and user file to use for the group
  uOpt = U 
  uFile = $KDB_ROOT_PATH/data/shared/streams.txt
  
  # use 32 bit q version
  qPath = Q32_PATH
  qHome = Q32_HOME

  [[stream.stream1]]
  type = q:stream/stream
  requires = core.rdb
  command = "q stream.q"
  port = $basePort + 1

  [[stream.stream2]]
  type = q:stream/stream
  requires = core.rdb
  command = "q stream.q"
  port = $basePort + 2

[group:external]              # settings for 'external' systems
  [[prod2.rdb]]               # component definition of type rdb on production2:2012
  type = c:rdb/rdb            # such configuration might be usefull for eodMng
  port = 2012
  host = production2
```