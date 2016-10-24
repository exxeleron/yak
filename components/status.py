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

import logging
import os
import sqlite3

from components.component import Component
from osutil import get_username


class StatusPersistance(object):
    """Manages persistence of processes status"""

    __DB_SCHEMA_1__ = \
    """
    PRAGMA journal_mode=WAL;

    CREATE TABLE IF NOT EXISTS components(
        uid VARCHAR PRIMARY KEY,
        typeid VARCHAR,
        pid INT,
        executed_cmd VARCHAR,
        log VARCHAR,
        stdout VARCHAR,
        stderr VARCHAR,
        stdenv VARCHAR,
        started TIMESTAMP,
        started_by VARCHAR,
        stopped TIMESTAMP,
        stopped_by VARCHAR
    );
    """

    __DB_SCHEMA_2__ = "ALTER TABLE components ADD COLUMN last_operation VARCHAR;"

    __DB_UPGRADE_STEPS__ = {
        1: __DB_SCHEMA_1__,
        2: __DB_SCHEMA_2__,
    }

    __ATTRS_COMPONENT__ = ["uid", "typeid", "pid", "executed_cmd", "last_operation", "log", "stdout", "stderr", "stdenv", "started", "started_by", "stopped", "stopped_by"]

    __UPSERT_STATUS__ = \
    "INSERT OR REPLACE INTO components(%s) VALUES(%s)" % \
        (", ".join(__ATTRS_COMPONENT__), "?, " * (len(__ATTRS_COMPONENT__) - 1) + "?")

    __SELECT_STATUS__ = "SELECT * from components"

    __DELETE_STATUS__ = "DELETE FROM components WHERE uid = ?"

    def __init__(self, statusfile):
        statuspath = os.path.split(statusfile)[0]
        if not os.path.exists(statuspath):
            os.makedirs(statuspath)

        self._statusfile = statusfile

        self._init_db_()

        self.__conn = self._connection_()
        self.__conn.row_factory = sqlite3.Row

    def _connection_(self):
        return sqlite3.connect(self._statusfile,
                               detect_types = sqlite3.PARSE_DECLTYPES,
                               check_same_thread = False,
                               timeout = 30.0)

    def _init_db_(self):
        connection = self._connection_()
        with connection:
            current_schema = connection.execute("PRAGMA user_version").fetchone()[0]
            target_schema = max(self.__DB_UPGRADE_STEPS__)
            if current_schema < target_schema:
                connection.isolation_level = "EXCLUSIVE"
                logger = logging.getLogger("yak")
                for step in range(current_schema + 1, target_schema + 1):
                    if step in self.__DB_UPGRADE_STEPS__:
                        logger.info("Upgrading status file db schema: [%d/%d]", step, target_schema, extra = {"user": get_username()})
                        connection.execute("BEGIN EXCLUSIVE")
                        connection.executescript(self.__DB_UPGRADE_STEPS__[step])
                        connection.execute("PRAGMA user_version={:d}".format(step))
                        connection.commit()

    def load(self):
        """Loads components status data from the status file"""
        components = dict()

        c = self.__conn.cursor()
        c.execute(self.__SELECT_STATUS__)
        for row in c.fetchall():
            args = dict(**row)
            args["status_persistance"] = self
            component = Component.create_instance(**args)
            components[component.uid] = component

        return components

    def save_status(self, component):
        """Saves component status in the status file"""
        data = [getattr(component, attr) for attr in self.__ATTRS_COMPONENT__]
        self.__conn.execute(self.__UPSERT_STATUS__, data)
        self.__conn.commit()

    def delete_status(self, uid):
        """Deletes satus od a single component from the status file"""
        self.__conn.execute(self.__DELETE_STATUS__, [uid])
        self.__conn.commit()
