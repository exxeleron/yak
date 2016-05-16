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
    log_file_pattern = re.compile("Logging to file\s*:\s*(?P<path>.+)$")
    rolled_log_pattern = re.compile("log continues in \s*(?P<path>.+)$", re.MULTILINE)

    def __init__(self, uid, **kwargs):
        self._logfile = None
        super(QComponent, self).__init__(uid, **kwargs)

    def _locate_log_file(self):
        if self.stdout and os.path.exists(self.stdout):
            with open(self.stdout, "r") as stdout:
                for line in stdout:
                    match = QComponent.log_file_pattern.search(line)
                    if match:
                        return os.path.normpath(match.group("path").strip())
                return None

    def _find_rolled_log(self, path):
        LOOKUP_LENGTH = 512
        while path and os.path.exists(path) and not osutil.is_empty(path):
            with open(path, "r") as stdout:
                file_size = osutil.file_size(path)
                lookup_pos = file_size - LOOKUP_LENGTH if file_size > LOOKUP_LENGTH else 0
                stdout.seek(lookup_pos)
                log = stdout.read()
                match = None
                for match in QComponent.rolled_log_pattern.finditer(log):
                    pass
                if match:
                    path = os.path.normpath(match.group("path").strip())
                    continue
            break

        return path

    def execute(self):
        if self.configuration.q_path:
            path = os.environ.get("PATH", "")
            os.environ["PATH"] = self.configuration.q_path + os.pathsep + path

        try:
            if self.configuration.u_file and not os.path.isfile(self.configuration.u_file):
                raise ComponentError("Cannot locate uFile: {0}".format(self.configuration.u_file))

            super(QComponent, self).execute()
        finally:
            if self.configuration.q_path:
                os.environ["PATH"] = path
            self.log = None

    def interactive(self):
        if self.configuration.q_path:
            path = os.environ.get("PATH", "")
            os.environ["PATH"] = self.configuration.q_path + os.pathsep + path

        try:
            if self.configuration.cpu_affinity:
                osutil.set_affinity(os.getpid(), self.configuration.cpu_affinity)

            if self.configuration.u_file and not os.path.isfile(self.configuration.u_file):
                raise ComponentError("Cannot locate uFile: {0}".format(self.configuration.u_file))

            env = self._bootstrap_environment()

            # overwrite logging configuration for interactive mode
            env["EC_LOG_DEST"] = "FILE,STDERR,CONSOLE"
            env["EC_LOG_LEVEL"] = "DEBUG"

            self.executed_cmd = str(self.configuration.full_cmd)
            p = subprocess.Popen(shlex.split(self.configuration.full_cmd, posix = False),
                                 cwd = self.configuration.bin_path,
                                 env = env
                                 )
            self.pid = p.pid
            super(QComponent, self).save_status()

            p.communicate()

            self.stopped = super(QComponent, self).timestamp()

            if p.returncode:
                raise ComponentError("Component {0} finished prematurely with code {1}".format(self.uid, p.returncode))
        finally:
            if self.configuration.q_path:
                os.environ["PATH"] = path

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
                stderr_size = osutil.file_size(self.stderr)
                if stderr_size >= 8:
                    with open(self.stderr, "r") as stderr:
                        stderr.seek(stderr_size - 10 if stderr_size > 10 else stderr_size - 8)
                        err = stderr.read()

                        if err[-8:].strip()[-6:] == "wsfull" : st = Status.WSFULL
                        if err[-10:].strip()[-8:] == "-w abort" : st = Status.WSFULL
        finally:
            return st


class QComponentConfiguration(ComponentConfiguration):
    """
    Specialized configuration for q processes.
    """

    typeid = "q"
    attrs = ComponentConfiguration.attrs + ["port", "multithreaded", "libs", "common_libs", "mem_cap", "u_opt", "u_file", "q_path", "q_home" ]

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
        self.q_path = self._get_value("qPath", cfg, None)
        self.q_home = self._get_value("qHome", cfg, None)
        if self.q_home:
            self.vars["QHOME"] = self.q_home

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
