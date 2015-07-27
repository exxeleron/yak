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

import sys
import time

from osutil import get_username
from components.component import ComponentConfiguration, Component, ComponentError, ConfigurationError
from components.q import QComponent
from components.status import StatusPersistance

from copy import copy
from collections import OrderedDict


class DependencyError(ComponentError):
    pass



class ComponentManager(object):
    """
    ComponentManager is responsible for keeping track of all managed components.
    It also serves as an operation gateway for managing components and provides
    operations like: start, stop, interrupt. 
    """

    def __init__(self, config_file, status_file):
        self._configuration, self._groups, self._namespaces = ComponentConfiguration.load_configuration(config_file)
        self._persistance = StatusPersistance(status_file)
        self._dependency_order = self._compute_dependencies()
        self.reload()

    def _compute_dependencies(self):
        deps = dict()
        reqs = dict()
        no_deps = list()
        ordered = list()

        for component in self._configuration.values():
            reqs[component.uid] = copy(component.requires)
            deps[component.uid] = list()

            if component.uid in component.requires:
                raise DependencyError("Self dependency found for component {0} -> {1}".format(component.uid, ", ".join(component.requires)))

        for component in self._configuration.values():
            if not component.requires:
                no_deps.append(component.uid)
            else:
                for uid in component.requires:
                    if not deps.has_key(uid):
                        raise DependencyError("Dependency to unmanaged component found in {0} -> {1}".format(component.uid, ", ".join(component.requires)))
                    deps[uid].append(component.uid)

        while no_deps:
            component = no_deps.pop(0)
            ordered.append(component)
            for dependent in deps[component]:
                reqs[dependent].remove(component)
                if not reqs[dependent]:
                    no_deps.append(dependent)

        stale = []
        for component, requires in reqs.iteritems():
            if requires:
                stale.append(component)

        if stale:
            raise DependencyError("Cannot determinate startup order for components {0}".format(", ".join(stale)))

        return ordered

    def _validate_preconditions(self, component_cfg):
        uname = get_username()
        if component_cfg.sys_user and not uname in component_cfg.sys_user:
            raise ComponentError("User {1} is not allowed to start component {0}".format(component_cfg.uid, uname))

        for required_uid in component_cfg.requires:
            if self._components.has_key(required_uid):
                required_component = self._components[required_uid]
                if not required_component.is_alive:
                    raise DependencyError("Cannot start component {0}, required component {1} not running".format(component_cfg.uid, required_uid))
            else:
                raise DependencyError("Cannot start component {0}, required component {1} not found".format(component_cfg.uid, required_uid))

    @property
    def dependencies_order(self):
        """Returns identifiers lists of managed components."""
        return self._dependency_order

    @property
    def configuration(self):
        """Returns configuration of managed components."""
        return self._configuration

    @property
    def components(self):
        """Returns managed components."""
        return self._components

    @property
    def groups(self):
        """Returns managed groups."""
        return self._groups

    @property
    def namespaces(self):
        """Returns managed namespaces."""
        return self._namespaces

    def reload(self):
        """
        Reloads components status snapshot from disk.
        """
        self._components = self._persistance.load()
        for configuration in self._configuration.itervalues():
            if not configuration.uid in self._components:
                self._components[configuration.uid] = Component.create_instance(typeid = configuration.typeid,
                                                                                uid = configuration.uid,
                                                                                configuration = configuration)
            else:
                self._components[configuration.uid].configuration = configuration

    def start(self, components, callback = None, pause_callback = None, **kwargs):
        """
        Starts multiple components. If component(s) is already running, nothing happens.
        @param components: list of identifier of the component
        @param callback: function to be executed after status of a component has been verified 
        @param pause_callback: function to be executed after while operation is paused
        @return: List of: tuples (uid, True if component has been started, False if the component is already running or ComponentError if component cannot be started). 
        """
        status = OrderedDict()
        start_wait = 0
        check_list = []

        def validate_started():
            if start_wait > 0 and any(s == True for s in status.values()):
                if pause_callback:
                    pause_callback(start_wait)
                time.sleep(start_wait)

            for component in check_list:
                try:
                    self._components[component].check_process()
                except Exception, e:
                    status[component] = e

                if callback:
                    callback(component, status[component])

        for component in components:
            requires = self._components[component].configuration.requires

            if requires and requires.intersection(check_list) and requires.intersection(components):
                validate_started()
                check_list = []
                start_wait = 0

            try:
                check_list.append(component)
                start_wait = max(start_wait, self._components[component].configuration.start_wait)
                status[component] = self._start(component, **kwargs)
            except Exception, e:
                status[component] = e

        validate_started()
        return status.items()

    def _start(self, uid, **kwargs):
        """
        Starts component with given uid. If component is already running, nothing happens.
        @param uid: identifier of the component 
        @return: True if component has been started, False if the component is already running.
        @raise ComponentError: if component cannot be started. 
        """
        component = self._components[uid]
        component_cfg = self._configuration[uid]

        if component.is_alive:
            return False

        self._validate_preconditions(component_cfg)

        overrides_arguments = kwargs and 'arguments' in kwargs and kwargs['arguments'] is not None
        if overrides_arguments:
            arguments_copy = component_cfg.command_args
            component_cfg.command_args = kwargs['arguments']

        try:
            component.initialize()
            component.execute()
            self._components[uid] = component
            return True
        except:
            raise ComponentError("Error while executing: '{0}'\n{1}".format(component_cfg.full_cmd, sys.exc_info()[1]))
        finally:
            self._persistance.save_status(component)
            if overrides_arguments:
                component_cfg.command_args = arguments_copy

    def stop(self, components, callback = None, pause_callback = None, **kwargs):
        """
        Stops multiple components. If component(s) is not running, nothing happens.
        @param components: list of identifier of the component
        @param callback: function to be executed after status of a component has been stopped/killed
        @param pause_callback: function to be executed after while operation is paused
        @return: List of: tuples (uid, True if component has been stopped, False if the component is not running or OSError if component cannot be stopped). 
        """
        status = OrderedDict()
        stop_wait = 0

        for component in components:
            stop_wait = max(stop_wait, self._components[component].configuration.stop_wait)
            try:
                status[component] = self._stop(component, **kwargs)
            except Exception, e:
                status[component] = e

        if pause_callback:
            pause_callback(stop_wait)
        time.sleep(stop_wait)

        for component in components:
            if self._components[component].is_alive:
                try:
                    status[component] = self._stop(component, True, **kwargs)
                except Exception, e:
                    status[component] = e

            if callback:
                callback(component, status[component])

        return status.items()

    def _stop(self, uid, force = False, **kwargs):
        """
        Stops component with given uid. If component is not running, nothing happens.
        @param uid: identifier of the component
        @return: True if component has been stopped, False if the component is not running.
        @raise OSError: if component cannot be stopped.
        """
        component = self._components[uid]

        if not component.is_alive:
            return False

        try:
            component.terminate()
            self._components[uid] = component
            return True
        finally:
            self._persistance.save_status(component)

    def console(self, uid, **kwargs):
        """
        Starts component with given uid with attached interactive console. If component is already running, nothing happens.
        @param uid: identifier of the component 
        @return: True if component has been started, False if the component is already running.
        @raise ComponentError: if component cannot be started. 
        """
        component = self._components[uid]
        component_cfg = self._configuration[uid]
        if component.is_alive:
            return False

        self._validate_preconditions(component_cfg)

        overrides_arguments = kwargs and 'arguments' in kwargs and kwargs['arguments'] is not None
        if overrides_arguments:
            arguments_copy = component_cfg.command_args
            component_cfg.command_args = kwargs['arguments']

        try:
            component.initialize(init_std_paths = False)
            component.interactive()
            return True
        finally:
            self._persistance.save_status(component)
            if overrides_arguments:
                component_cfg.command_args = arguments_copy

    def interrupt(self, components, callback = None, pause_callback = None, **kwargs):
        """
        Sends interrupt signal to multiple components. If component(s) is not running, nothing happens. (UNIX only)
        @param components: list of identifier of the component 
        @param callback: function to be executed after status of a component has been interrupted
        @param pause_callback: function to be executed after while operation is paused
        @return: List of: tuples (uid, True if component has been interrupted, False if the component is not running or OSError if component cannot be interrupted). 
        """
        status = OrderedDict()

        for component in components:
            try:
                status[component] = self._interrupt(component, **kwargs)
            except Exception, e:
                status[component] = e

            if callback:
                callback(component, status[component])

        return status.items()

    def _interrupt(self, uid, **kwargs):
        """
        Sends interrupt signal to component with given uid. If component is not running, nothing happens. (UNIX only)
        @param uid: identifier of the component
        @return: True if component has been interrupted, False if the component is not running.
        @raise OSError: if component cannot be interrupted.
        """
        component = self._components[uid]
        if not component.is_alive:
            return False

        try:
            component.interrupt()
            return True
        finally:
            self._persistance.save_status(component)

