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
import unittest

try:
    from collections import OrderedDict
except ImportError:  # python < 2.7 -> try to import ordereddict
    from ordereddict import OrderedDict

from components.component import ComponentConfiguration, ConfigurationError, TimestampMode
from components.q import QComponentConfiguration
from components.manager import ComponentManager, DependencyError



os.environ["LOG_ROOT"] = "_log_"
os.environ["DATA_ROOT"] = "_data_"
os.environ["BIN_ROOT"] = "_bin_"



class TestConfiguration(unittest.TestCase):

    REF_CFG = OrderedDict([("core.hdb", QComponentConfiguration(tuple(("core", "hdb")),
                                                              command = "q hdb.q -init 1b, 3s",
                                                              requires = set([]),
                                                              bin_path = "/opt/core/hdb",
                                                              data_path = "_data_",
                                                              log_path = "_log_/hdb",
                                                              start_wait = 3,
                                                              sys_user = ["tcore", "root"],
                                                              cpu_affinity = [0, 1],
                                                              port = 15005,
                                                              libs = [],
                                                              common_libs = ["clA"],
                                                              multithreaded = False,
                                                              kdb_user = "username",
                                                              kdb_password = "p@ssw0rd",
                                                              timestamp_mode = TimestampMode.UTC,
                                                              silent = False,
                                                              q_path = None,
                                                              q_home = None,
                                                              ),),
                           ("core.rdb", QComponentConfiguration(tuple(("core", "rdb")),
                                                              command = "q rdb.q",
                                                              requires = set(["core.hdb"]),
                                                              bin_path = "/opt/core/rdb",
                                                              data_path = "_data_",
                                                              log_path = "_log_/rdb",
                                                              start_wait = 3,
                                                              sys_user = ["tcore", "root"],
                                                              cpu_affinity = [0, 1],
                                                              port = -16000,
                                                              libs = ["libA", "libB"],
                                                              common_libs = ["clA"],
                                                              multithreaded = True,
                                                              kdb_user = "username",
                                                              kdb_password = "p@ssw0rd",
                                                              timestamp_mode = TimestampMode.UTC,
                                                              silent = False,
                                                              q_path = None,
                                                              q_home = None,
                                                              ),),
                           ("core.monitor", ComponentConfiguration(tuple(("core", "monitor")),
                                                                 command = "python monitor.py",
                                                                 requires = set(["core.rdb", "core.hdb"]),
                                                                 bin_path = "/opt/core/monitor",
                                                                 data_path = "_data_",
                                                                 log_path = "_log_/monitor",
                                                                 start_wait = 3,
                                                                 sys_user = ["tcore", "root"],
                                                                 cpu_affinity = [0, 1],
                                                                 timestamp_mode = TimestampMode.UTC,
                                                                 silent = False,
                                                                 ),),
                           ("cep.cep_7", QComponentConfiguration(tuple(("cep", "cep_7")),
                                                               command = "q cep.q",
                                                               requires = set(["core.rdb"]),
                                                               bin_path = ".",
                                                               data_path = "_data_",
                                                               log_path = "_log_/cep_7",
                                                               start_wait = 1,
                                                               sys_user = [],
                                                               cpu_affinity = [],
                                                               port = 16107,
                                                               libs = [],
                                                               common_libs = [],
                                                               multithreaded = False,
                                                               kdb_user = "tcep",
                                                               kdb_password = "$h@rd!",
                                                               u_opt = "U",
                                                               u_file = "optfile",
                                                               timestamp_mode = TimestampMode.UTC,
                                                               silent = False,
                                                               ),),
                           ("cep.python", ComponentConfiguration(tuple(("cep", "python")),
                                                                command = "python",
                                                                requires = set([]),
                                                                bin_path = ".",
                                                                data_path = "_data_",
                                                                log_path = "_log_/python",
                                                                start_wait = 1,
                                                                sys_user = [],
                                                                timestamp_mode = TimestampMode.UTC,
                                                                silent = True,
                                                                cpu_affinity = [],))]
                          )

    def testSample(self):
        c = ComponentConfiguration.load_configuration("components/test/sample.cfg")[0]
        for component_id in c:
            component = c[component_id]
            for a in component.attrs:
                actual = getattr(component, a)
                expected = getattr(TestConfiguration.REF_CFG[component.uid], a)
                self.assertEqual(actual, expected, "%s.%s\nexpected: %s\nactual: %s" % (component_id, a, expected, actual))

    def testEnvBootstrap(self):
        c = ComponentManager("components/test/sample.cfg", "components/test/test.status")
        env = c.components["core.hdb"]._bootstrap_environment()

        self.assertEqual("core.hdb", env["EC_COMPONENT_ID"])
        self.assertEqual("hdb", env["EC_COMPONENT"])
        self.assertEqual("core", env["EC_GROUP"])
        self.assertEqual("hdb", env["EC_COMPONENT_TYPE"])

        self.assertEqual("_bin_/etc_shared/,/app/etc/hdb", env["EC_ETC_PATH"])
        self.assertEqual("LOG,MONITOR", env["EC_EVENT_DEST"])
        self.assertEqual("/data/shared/events/", env["EC_EVENT_PATH"])


    def testDependencyOrder(self):
        c = ComponentManager("components/test/sample.cfg", "components/test/test.status")
        self.assertEqual(c.dependencies_order, ["core.hdb", "cep.python", "core.rdb", "core.monitor", "cep.cep_7"])

    def testDependencyOrderFailSelfDependency(self):
        with self.assertRaises(DependencyError):
            ComponentManager("components/test/self_dep.cfg", "components/test/test.status")

    def testDependencyOrderFailCircularDependency(self):
        with self.assertRaises(DependencyError):
            ComponentManager("components/test/circular_dep.cfg", "components/test/test.status")

    def testDependencyOrderFailExternalDependency(self):
        with self.assertRaises(DependencyError):
            ComponentManager("components/test/ext_dep.cfg", "components/test/test.status")



if __name__ == "__main__":
    unittest.main()
