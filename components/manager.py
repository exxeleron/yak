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

from osutil import get_username
from components.component import ComponentConfiguration, Component, ComponentError, ConfigurationError
from components.q import QComponent
from components.status import StatusPersistance

from copy import copy

class ComponentManager(object):
    """
    ComponentManager is responsible for keeping track of all managed components.
    It also serves as an operation gateway for managing components and provides
    operations like: start, stop, interrupt. 
    """

    def __init__(self, config_file, status_file):
        self._configuration, self._groups = ComponentConfiguration.load_configuration(config_file)
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
                raise ConfigurationError("Self dependency found for component {0} -> {1}".format(component.uid, ", ".join(component.requires)))

        for component in self._configuration.values():
            if not component.requires:
                no_deps.append(component.uid)
            else:
                for uid in component.requires:
                    if not deps.has_key(uid):
                        raise ConfigurationError("Dependency to unmanaged component found in {0} -> {1}".format(component.uid, ", ".join(component.requires)))
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
            raise ConfigurationError("Cannot determinate startup order for components {0}".format(", ".join(stale)))

        return ordered

    def _validate_preconditions(self, component_cfg):
        uname = get_username()
        if component_cfg.sys_user and not uname in component_cfg.sys_user:
            raise ComponentError("User {1} is not allowed to start component {0}".format(component_cfg.uid, uname))

        for required_uid in component_cfg.requires:
            if self._components.has_key(required_uid):
                required_component = self._components[required_uid]
                if not required_component.is_alive:
                    raise ComponentError("Cannot start component {0}, required component {1} not running".format(component_cfg.uid, required_uid))
            else:
                raise ComponentError("Cannot start component {0}, required component {1} not found".format(component_cfg.uid, required_uid))

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

    def start(self, uid):
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
        try:
            component.initialize()
            component.execute()
            self._components[uid] = component
            return True
        except:
            raise ComponentError("Error while executing: '{0}' {1}".format(component.executed_cmd, sys.exc_info()[1]))
        finally:
            self._persistance.save_status(component)

    def stop(self, uid):
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

    def console(self, uid):
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
        component.initialize()
        component.interactive()
        return True

    def interrupt(self, uid):
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

