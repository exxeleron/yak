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
import sys


__all__ = ["is_alive", "is_empty", "execute",
           "terminate", "interrupt", "get_command_line",
           "get_username", "symlink", "get_affinity", "set_affinity",
           "get_cpu_sys", "get_cpu_user", "get_cpu_percent",
           "get_mem_sys", "get_mem_user", "get_mem_percent"]

def __nop__(*args):
    pass

def set_affinity(pid, cpus):
    try:
        p = psutil.Process(pid)
        return p.cpu_affinity(cpus)
    except psutil.NoSuchProcess:
        pass

def get_affinity(pid):
    try:
        p = psutil.Process(pid)
        return p.cpu_affinity()
    except psutil.NoSuchProcess:
        pass


if sys.platform.lower().startswith("win32"):
    from osutil._win32 import *
elif sys.platform.lower().startswith("linux"):
    from osutil._linux import *
elif sys.platform.lower().startswith("darwin"):
    from osutil._osx import *
else:
    raise NotImplementedError("%s platform is not supported" % sys.platform)


def is_empty(path):
    return (not path) or (not os.path.exists(path)) or (os.path.isfile(path) and os.stat(path).st_size == 0)

def file_size(path):
    return os.stat(path).st_size if path and os.path.isfile(path) else 0


# generic from psutil
def get_cpu_sys(pid):
    try:
        p = psutil.Process(pid)
        return p.cpu_times().system
    except psutil.NoSuchProcess:
        pass

def get_cpu_user(pid):
    try:
        p = psutil.Process(pid)
        return p.cpu_times().user
    except psutil.NoSuchProcess:
        pass

def get_cpu_percent(pid):
    try:
        p = psutil.Process(pid)
        return p.cpu_percent(interval = None)
    except psutil.NoSuchProcess:
        pass

def get_memory_rss(pid):
    try:
        p = psutil.Process(pid)
        return p.memory_info().rss
    except psutil.NoSuchProcess:
        pass

def get_memory_vms(pid):
    try:
        p = psutil.Process(pid)
        return p.memory_info().vms
    except psutil.NoSuchProcess:
        pass

def get_memory_percent(pid):
    try:
        p = psutil.Process(pid)
        return p.memory_percent()
    except psutil.NoSuchProcess:
        pass
