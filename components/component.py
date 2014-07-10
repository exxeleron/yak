#
#  Copyright (c) 2011-2014 Exxeleron GmbH
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import os
import re
import shlex
import subprocess
import time

try:
    from collections import OrderedDict
except ImportError:  # python < 2.7 -> try to import ordereddict
    from ordereddict import OrderedDict

from configobj import ConfigObj
from datetime import datetime as dt
from string import Template

import osutil

from components import ComponentManagerError
from components.utils import to_underscore


DT_FORMAT = "%Y.%m.%dT%H.%M.%S"
VALID_UID_RE = re.compile("^\w+\.\w+$|^\w+\.\w+_\d+$")
MISSING_ENV_VARS_RE = re.compile("\$\w+|\$\{\w+\}|%\w+%")


def initialize_plugins(cls):
    """Initializes dictionary containing subclass(plugins) of particular class."""
    plugins = { cls.typeid : cls }
    plugins.update(dict([(x.typeid, x) for x in itersubclasses(cls)]))
    cls.plugins = plugins
    return cls


def itersubclasses(cls, _seen = None):
    if not isinstance(cls, type):
        raise TypeError("itersubclasses must be called with "
                        "new-style classes, not %.100r" % cls)
    if _seen is None: _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError:  # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub


class ComponentError(ComponentManagerError):
    pass


class ConfigurationError(ComponentManagerError):
    pass


class Status(object):
    DISTURBED = "DISTURBED"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"
    WSFULL = "WSFULL"

running_statuses = (Status.RUNNING, Status.DISTURBED)


class Component(object):
    """
    Base class for components objects. Represents single operational system process.
    """

    typeid = "cmd"
    attrs = ["uid", "status", "pid", "executed_cmd", "log", "stdout", "stderr", "stdenv", "started", "started_by", "stopped", "stopped_by"]

    def __init__(self, uid, **kwargs):
        self.uid = str(uid)
        self.configuration = kwargs.get("configuration")

        self.stdenv = None
        for a in self.attrs[2:]:  # skip uid and read-only properties
            setattr(self, a, kwargs.get(a))

    def __str__(self):
        return "<{1}> {0} [{3}]: {2}".format(self.uid, self.typeid, self.cmd, self.pid)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def initialize(self):
        self.started = dt.utcnow()
        self.started_by = osutil.get_username()

        self.stopped = None
        self.stopped_by = None

        self.data_path = self.configuration.data_path
        self.log_path = self.configuration.log_path

        tstamp = self.started.strftime(DT_FORMAT)

        if not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

        self.stdout = os.path.join(self.log_path, "{0}_{1}.out".format(self.uid, tstamp))
        self.stderr = os.path.join(self.log_path, "{0}_{1}.err".format(self.uid, tstamp))
        self.stdenv = os.path.join(self.log_path, "{0}_{1}.env".format(self.uid, tstamp))

    def _bootstrap_environment(self):
        env = os.environ.copy()
        env.update(self.configuration.vars)
        env.update(self.configuration.env)
        
        if self.stdenv:
            with open(self.stdenv, "w") as f:
                for key in env.keys():
                    f.write("{0}: {1}\n".format(key, env[key]))
            
        return env

    def execute(self):
        if self.configuration.cpu_affinity:
            osutil.set_affinity(os.getpid(), self.configuration.cpu_affinity)

        self.executed_cmd = str(self.configuration.full_cmd)
        p = osutil.execute(cmd = shlex.split(self.configuration.full_cmd, posix = False),
                           stdout = open(self.stdout, "w"),
                           stderr = open(self.stderr, "w"),
                           bin_path = self.configuration.bin_path,
                           env = self._bootstrap_environment()
                           )
        self.pid = p.pid

        if self.configuration.start_wait:
            if self.configuration.start_wait > 0:
                time.sleep(self.configuration.start_wait)
                if p.poll():
                    self.pid = None
                    raise ComponentError("Component {0} finished prematurely with code {1}".format(self.uid, p.returncode))
            else:
                p.wait()
                self.pid = None
                self.stopped = dt.utcnow()

    def interactive(self):
        if self.configuration.cpu_affinity:
            osutil.set_affinity(os.getpid(), self.configuration.cpu_affinity)

        p = subprocess.Popen(shlex.split(self.configuration.full_cmd, posix = False),
                             cwd = self.configuration.bin_path,
                             env = self._bootstrap_environment()
                             )
        p.communicate()
        if p.returncode:
            raise ComponentError("Component {0} finished prematurely with code {1}".format(self.uid, p.returncode))

    def terminate(self):
        try:
            osutil.terminate(self.pid, self.configuration.stop_wait)
            self.stopped = dt.utcnow()
            self.stopped_by = osutil.get_username()
            self.pid = None
        except OSError, e:
            raise ComponentError(e)

    def interrupt(self):
        try:
            osutil.interrupt(self.pid)
        except OSError, e:
            raise ComponentError(e)

    @property
    def is_alive(self):
        """Returns true if component is alive, false otherwise"""
        if self.pid and osutil.is_alive(int(self.pid)):
            cmd = shlex.split(str(self.executed_cmd), posix = False)
            proc_cmd = self.proc_cmd
            return not proc_cmd or not cmd or proc_cmd == cmd
        else:
            return False

    @property
    def status(self):
        """Returns status of a component"""
        if self.is_alive:
            return Status.RUNNING if osutil.is_empty(self.stderr) else Status.DISTURBED
        elif not self.started or self.stopped:
            self.pid = None
            return Status.STOPPED
        else:
            self.pid = None
            return Status.TERMINATED

    @property
    def proc_cmd(self):
        """Returns command reported by OS associated with the component PID"""
        return osutil.get_command_line(self.pid) if self.pid else None

    @property
    def cpu_user(self):
        """Returns cpu time in user mode for a component"""
        return osutil.get_cpu_user(self.pid) if self.status in running_statuses else 0.0

    @property
    def cpu_sys(self):
        """Returns cpu time in system mode for a component"""
        return osutil.get_cpu_sys(self.pid) if self.status in running_statuses else 0.0

    @property
    def mem_usage(self):
        """Returns memory usage for a component"""
        return osutil.get_memory_percent(self.pid) if self.status in running_statuses else 0.0

    @property
    def mem_rss(self):
        """Returns rss memory used by a component"""
        return osutil.get_memory_rss(self.pid) / 1024 if self.status in running_statuses else 0

    @property
    def mem_vms(self):
        """Returns vms memory used by a component"""
        return osutil.get_memory_vms(self.pid) / 1024 if self.status in running_statuses else 0

    @staticmethod
    def create_instance(typeid, uid, configuration = None, **kwargs):
        """
        Factory method: creates new instance of component for requested type.
        @param typeid:
            string identifier of requested component type
        @param uid:
            unique identifier of new component
        """
        if not hasattr(Component, "plugins"):
            initialize_plugins(Component)
        return Component.plugins[typeid](uid = uid, configuration = configuration, **kwargs)


class ComponentConfiguration(object):
    """
    Base class for representing component configurations.
    """

    typeid = "cmd"
    attrs = ["uid", "full_cmd", "requires", "command", "command_args", "bin_path", "data_path", "log_path", "cpu_affinity", "start_wait", "stop_wait", "sys_user"]

    def __init__(self, uid, **kwargs):
        self.uid = "{0}.{1}".format(*uid) if len(uid) <= 2 else "{0}.{1}_{2}".format(*uid)
        if not VALID_UID_RE.match(self.uid):
            raise ConfigurationError("{0} is an invalid component identifier".format(self.uid))

        self.gid = uid[0]
        self.cid = uid[1]
        self.instance = uid[2] if len(uid) > 2 else None

        self.vars = dict()

        for a in self.attrs[2:]:  # skip uid and read-only properties
            setattr(self, a, kwargs.get(a))

    def __str__(self):
        return "<{1}> {0}: {2}".format(self.uid, self.typeid, self.command)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def _expand_variables(self, value, variables = None):
        bootstrap = dict(self.vars)
        if variables:
            bootstrap.update(variables)

        if isinstance(value, basestring):
            value = os.path.expandvars(Template(value).safe_substitute(bootstrap))
            if MISSING_ENV_VARS_RE.search(value):
                raise ConfigurationError("Unresolved variable {0} found in component {1}".format(value, self.uid))
            return value
        else:
            return value

    def _get_raw_value(self, attr, cfg, default = None, required = False):
        value = default
        for cfg_group in cfg:
            if cfg_group.has_key(attr):
                value = cfg_group[attr]
                break
        if value and isinstance(value, basestring) and value.upper() == "NULL":
            value = None
        if required and not value:
            raise ConfigurationError("Component {1} is missing required parameter {0}".format(attr, self.uid))
        return value

    @staticmethod
    def _int_(value):
        try:
            return int(value)
        except:
            return None

    @staticmethod
    def _float_(value):
        try:
            return float(value)
        except:
            return None

    @staticmethod
    def _bool_(value):
        if value is True or value is False:
            return value
        s = str(value).strip().lower()
        return not s in ["false", "f", "n", "0", ""]

    def _get_value(self, attr, cfg, default = None, required = False):
        return self._expand_variables(self._get_raw_value(attr, cfg, default))

    def _get_list(self, attr, cfg, default = []):
        raw_value = self._get_raw_value(attr, cfg, default)
        return [self._expand_variables(v) for v in raw_value] if isinstance(raw_value, list) else [self._expand_variables(raw_value)]

    def _get_file(self, attr, cfg, default = None):
        f = self._get_value(attr, cfg, default)
        return os.path.normpath(f) if f else f

    def _get_path(self, attr, cfg, default = None):
        path = self._get_value(attr, cfg, default)
        return os.path.normpath(path).replace("\\", "/") if path else os.curdir

    def _get_path_list(self, attr, cfg, default = []):
        paths = self._get_list(attr, cfg)
        return [os.path.normpath(path).replace("\\", "/") if path else os.curdir for path in paths]

    def _get_env_vars_list(self, cfg):
        env_keys = self._get_list("export", cfg)
        raw_values = [self._get_value(x, cfg) for x in env_keys]
        env_values = [",".join(x) if type(x) == list else (x if x else "") for x in raw_values]

        env = dict(zip(["EC_" + to_underscore(key) for key in env_keys], map(self._expand_variables, env_values)))
        return env

    def parse(self, cfg):
        """
        Parses configuration for particular component.
        """
        self.vars = dict()
        self.vars["EC_COMPONENT_ID"] = self.uid
        self.vars["EC_COMPONENT"] = self.cid
        self.vars["EC_GROUP"] = self.gid
        self.vars["EC_COMPONENT_INSTANCE"] = self.instance if self.instance else ""

        ctype1 = self._get_raw_value("type", cfg).split(":")
        if len(ctype1) <= 1 :
            self.vars["EC_COMPONENT_PKG"] = ""
            self.vars["EC_COMPONENT_TYPE"] = ""
        else :
            ctype2 = ctype1[1].split("/")
            if len(ctype2) <= 1 :
                self.vars["EC_COMPONENT_PKG"] = ""
                self.vars["EC_COMPONENT_TYPE"] = ctype2[0]
            else :
                self.vars["EC_COMPONENT_PKG"] = ctype2[0]
                self.vars["EC_COMPONENT_TYPE"] = ctype2[1]

        self.command = self._get_value("command", cfg, required = True)
        self.requires = set([s if VALID_UID_RE.match(s) else "{0}.{1}".format(self.gid, s) for s in self._get_list("requires", cfg)])
        self.bin_path = self._get_path("binPath", cfg)
        self.data_path = self._get_path("dataPath", cfg)
        self.log_path = self._get_path("logPath", cfg)
        self.cpu_affinity = [self._int_(v) for v in self._get_list("cpuAffinity", cfg)]
        self.start_wait = self._float_(self._get_value("startWait", cfg, 1))
        self.stop_wait = self._float_(self._get_value("stopWait", cfg, 1))
        self.sys_user = self._get_list("sysUser", cfg)
        self.command_args = self._get_value("commandArgs", cfg)

        self.env = self._get_env_vars_list(cfg)

    @property
    def full_cmd(self):
        """Returns full command required to start component."""
        cmd = self.command

        if self.command_args:
            cmd += " {0}".format(self.command_args)

        return cmd

    @staticmethod
    def load_configuration(filename):
        """
        Loads configuration from a file.
        @param filename: name of the file to be loaded
        """
        if not os.path.exists(filename):
            raise ConfigurationError("Cannot locate configuration file: {0}".format(filename))

        confobj = ConfigObj(filename)
        config = OrderedDict()
        groups = dict()

        global_params = dict()
        for param in confobj.scalars:
            global_params[param] = confobj[param]

        for g_header in confobj.sections:
            group = g_header.split(":")[1]
            if not groups.has_key(group) :
                groups[group] = []

            for c_header in confobj[g_header].sections:
                c_params = c_header.split(":")
                c_namespace, c_id = c_params[0].split(".")
                c_type = confobj[g_header][c_header]["type"].split(":")[0]

                if (not c_type == "c"):
                    if len(c_params) == 1:
                        s = ComponentConfiguration.create_instance(c_type,
                                                                 tuple((c_namespace, c_id)),
                                                                 tuple((confobj[g_header][c_header], confobj[g_header], global_params)))
                        config[s.uid] = s
                        groups[group].append(s.uid)
                    else:  # multiple instances
                        c = c_params[1]
                        clones = map(int, c[1:-1].split(",")) if c.startswith("(") and c.endswith(")") else range(int(c))
                        for i in clones:
                            s = ComponentConfiguration.create_instance(c_type,
                                                                     tuple((c_namespace, c_id, str(i))),
                                                                     tuple((confobj[g_header][c_header], confobj[g_header], global_params)))
                            config[s.uid] = s
                            groups[group].append(s.uid)

        for group, uids in groups.iteritems():
            for uid in uids:
                if not uid in config:
                    raise ConfigurationError("Alias {0} references unmanaged component {1}".format(group, uid))

        return (config, groups)

    @staticmethod
    def create_instance(typeid, uid, cfg):
        """
        Factory method: creates new instance of component configuration for requested type.
        @param typeid:
            string identifier of requested component type
        @param uid:
            tuple with unique identifier of new component
        @param cfg:
            tuple containing dictionaries with configuration ordered by priority
        """
        if not hasattr(ComponentConfiguration, "plugins"):
            initialize_plugins(ComponentConfiguration)
        sc = ComponentConfiguration.plugins[typeid](uid = uid)
        sc.parse(cfg)
        return sc


