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

import osutil

from components.component import Component, ComponentError, ComponentConfiguration, Status


class QComponent(Component):
    """
    Specialized component class which represents running q process.
    """

    typeid = "q"

    def __init__(self, uid, **kwargs):
        self._logfile = None
        super(QComponent, self).__init__(uid, **kwargs)

    def _locate_log_file(self):
        if self.stdout and os.path.exists(self.stdout):
            with open(self.stdout, 'r') as stdout:
                for line in stdout:
                    match = re.search('Logging to file\s*:\s*(?P<path>.+)$', line)
                    if match:
                        return os.path.normpath(match.group('path').strip())
                return None

    def _find_rolled_log(self, path):
        while path and os.path.exists(path) :
            with open(path, 'r') as stdout:
                lastLines = stdout.readlines()[-2:]
                matched = False
                for line in lastLines :
                    match = re.search('log continues in \s*(?P<path>.+)$', line)
                    if match :
                        path = os.path.normpath(match.group('path').strip())
                        matched = True
                        break
                if not matched :
                    return path
        return path

    def execute(self):
        try:
            super(QComponent, self).execute()
        finally:
            self.log = None

    def interactive(self):
        if self.configuration.cpu_affinity:
            osutil.set_affinity(os.getpid(), self.configuration.cpu_affinity)

        env = self._bootstrap_environment()

        # overwrite logging configuration for interactive mode
        env["EC_LOG_DEST"] = "FILE,STDERR,CONSOLE"
        env["EC_LOG_LEVEL"] = "DEBUG"

        p = subprocess.Popen(shlex.split(self.configuration.full_cmd, posix = False),
                             cwd = self.configuration.bin_path,
                             env = env
                             )
        p.communicate()
        if p.returncode:
            raise ComponentError("Component {0} finished prematurely with code {1}".format(self.uid, p.returncode))

    @property
    def log(self):
        if not self._logfile:
            self._logfile = self._locate_log_file()
        self._logfile = self._find_rolled_log(self._logfile)
        return self._logfile

    @log.setter
    def log(self, logfile):
        self._logfile = logfile

    @property
    def port(self):
        """Returns port"""
        return self.configuration.port

    @property
    def mem_cap(self):
        """Returns mem_cap"""
        return self.configuration.mem_cap

    @property
    def status(self):
        """Returns status of a component"""
        st = super(QComponent, self).status
        try:
            if (st == Status.TERMINATED or st == Status.DISTURBED) and not osutil.is_empty(self.stderr):
                stderr = open(self.stderr, "r")
                err = osutil.open_mmap(stderr.fileno())
                if err[-8:].strip()[-6:] == "wsfull" : st = Status.WSFULL
                if err[-10:].strip()[-8:] == "-w abort" : st = Status.WSFULL
        finally:
            return st


class QComponentConfiguration(ComponentConfiguration):
    """
    Specialized configuration for q processes.
    """

    typeid = "q"
    attrs = ComponentConfiguration.attrs + ["port", "multithreaded", "libs", "common_libs", "mem_cap", "u_opt", "u_file" ]

    def _get_port(self, cfg, default = 0):
        port_attr = "basePort"
        base_port = self._int_(self._expand_variables(cfg[1][port_attr]) if cfg[1].has_key(port_attr) else self._expand_variables(cfg[2].get(port_attr, default)))

        component_val = self._expand_variables(cfg[0].get("port", default), variables = {"basePort": base_port})
        if not component_val:
            return base_port
        else:
            return eval(component_val, {"__builtins__":None}, {})

    def parse(self, cfg):
        ComponentConfiguration.parse(self, cfg)
        self.multithreaded = self._bool_(self._get_value("multithreaded", cfg, False))
        self.port = self._get_port(cfg)
        self.port = self.port * (-1 if self.multithreaded else 1) if self.port else self.port
        self.libs = self._get_list("libs", cfg, [])
        self.common_libs = self._get_list("commonLibs", cfg, [])
        self.mem_cap = self._get_value("memCap", cfg)
        self.mem_cap = self._int_(self.mem_cap) if self.mem_cap else None
        self.u_opt = self._get_value("uOpt", cfg)
        self.u_file = self._get_file("uFile", cfg)

    @property
    def full_cmd(self):
        """Returns full command required to start component."""
        cmd = self.command

        if self.command_args:
            cmd += " {0}".format(self.command_args)

        if self.common_libs:
            cmd += " -commonLibs {0}".format(" ".join(self.common_libs))

        if self.libs:
            cmd += " -libs {0}".format(" ".join(self.libs))

        if self.port:
            cmd += " -p {0:d}".format(self.port)

        if self.mem_cap and self.mem_cap > 0:
            cmd += " -w {0:d}".format(self.mem_cap)

        if self.u_opt:
            cmd += " -{0} {1}".format(self.u_opt, self.u_file)

        return cmd


class QBatch(QComponent):
    typeid = "b"

    @property
    def status(self):
        st = super(QBatch, self).status
        return st if st != Status.TERMINATED else Status.STOPPED

class QBatchConfiguration(QComponentConfiguration):
    """Batch processes configuration definition. """
    typeid = "b"

