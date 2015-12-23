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

import shlex
import osutil

from datetime import datetime as dt
from component import running_statuses, Status, ComponentError


class DetachedComponent(object):
    """
    Represents component detached from the configuration.
    """

    typeid = "cmd"
    attrs = ["uid", "status", "pid", "executed_cmd", "log", "stdout", "stderr", "stdenv", "started", "started_by", "stopped", "stopped_by"]

    def __init__(self, uid, **kwargs):
        self.uid = str(uid)
        self.configuration = DetachedConfiguration()
        self._status_persistance = kwargs.get("status_persistance")

        for a in self.attrs[2:]:  # skip uid and read-only properties
            setattr(self, a, kwargs.get(a))

    def __str__(self):
        return "<{1}> {0} [{3}]: {2}".format(self.uid, self.typeid, self.cmd, self.pid)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def timestamp(self):
        return dt.utcnow()

    def execute(self):
        raise ComponentError("Detached component {0} cannot be started".format(self.uid))

    def interactive(self):
        raise ComponentError("Detached component {0} cannot be started".format(self.uid))

    def terminate(self, force = False):
        osutil.terminate(self.pid, force)
        self.stopped = self.timestamp()
        self.stopped_by = osutil.get_username()
        self.pid = None

    def interrupt(self):
        osutil.interrupt(self.pid)

    def save_status(self):
        """Saves component status in the status file"""
        if self._status_persistance:
            self._status_persistance.save_status(self)
            
    def check_process(self):
        pass

    @property
    def is_alive(self):
        """Returns true if component is alive, false otherwise"""
        if self.pid:
            if osutil.is_alive(int(self.pid)):
                cmd = shlex.split(str(self.executed_cmd), posix = False)
                proc_cmd = self.proc_cmd
                return not proc_cmd or not cmd or proc_cmd == cmd
            else:
                self.pid = None
                self.save_status()
                return False
        else:
            return False

    @property
    def status(self):
        """Returns status of a component"""
        if self.is_alive:
            return Status.DETACHED
        elif not self.started or self.stopped:
            return Status.STOPPED
        else:
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
        memrss = osutil.get_memory_rss(self.pid)
        return memrss / 1024 if self.status in running_statuses and isinstance(memrss, (int, long)) else 0

    @property
    def mem_vms(self):
        """Returns vms memory used by a component"""
        memvms = osutil.get_memory_vms(self.pid)
        return memvms / 1024 if self.status in running_statuses and isinstance(memvms, (int, long)) else 0


class DetachedConfiguration(object):
    def __getattr__(self, name):
        return None