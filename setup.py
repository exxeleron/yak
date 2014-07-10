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
import shutil

from distutils.core import setup, Command


class bbfreeze(Command):
    description = "bbfreeze wrapper"
    user_options = [("name=", "n", "name"),
                    ("version=", "v", "version"),
                    ("platform=", "p", "platform suffix"),
                    ]

    def initialize_options(self):
        self.include_py = False
        self.name = None
        self.version = None
        self.platform = None
        self.app_name = None
        self.includes = None
        self.excludes = None
        self.extra_libs = None
        self.data_files = None
        self.dist_dir = None

    def finalize_options(self):
        from distutils.util import get_platform
        self.name = self.name if self.name else self.distribution.metadata.name
        self.version = self.version if self.version else self.distribution.metadata.version
        self.platform = self.platform if self.platform else get_platform()
        self.app_name = "%s-%s-%s" % (self.name, self.version, self.platform)
        self.includes = self.includes if self.includes else ()
        self.excludes = self.excludes if self.excludes else ()
        self.extra_libs = self.extra_libs if self.extra_libs else []
        self.data_files = self.data_files if self.data_files else []
        self.dist_dir = self.dist_dir if self.dist_dir else os.path.join("dist", self.app_name)

    def run(self):
        from bbfreeze import Freezer
        from distutils.archive_util import make_archive

        freezer = Freezer(distdir = self.dist_dir,
                          includes = self.includes,
                          excludes = self.excludes)
        freezer.include_py = self.include_py

        if self.distribution.scripts:
            for script in self.distribution.scripts:
                freezer.addScript(script, gui_only = False)

        # execute freeze
        freezer()
        # include extra libs - hack for Unix
        if self.extra_libs:
            print "extra_libs: ", self.extra_libs
            for lib in self.extra_libs:
                shutil.copy(lib, self.dist_dir)
        # include data_files
        if self.data_files:
            print "data_files: ", self.data_files
            for df in self.data_files:
                shutil.copy(df, self.dist_dir)
        # archived distribution
        archived = make_archive(self.app_name, "zip", self.dist_dir)
        package = os.path.join("dist", self.app_name + ".zip")
        if os.path.exists(package):
            os.unlink(package)
        shutil.move(archived, package)


class imprint(Command):
    description = "imprint application scripts"
    user_options = [("tstamp=", "t", "tstamp"),
                    ("version=", "v", "version"),
                    ]

    def initialize_options(self):
        self.tstamp = None
        self.version = None

    def finalize_options(self):
        from datetime import datetime
        metadata = self.distribution.metadata
        if self.tstamp is None:
            self.tstamp = datetime.now().strftime("%Y%m%d%H%M%S")
        if self.version is None:
            self.version = metadata.version

    def run(self):
        metadata = self.distribution.metadata

        if self.distribution.scripts:
            imprint_pt = re.compile(r"IMPRINT.+### imprint ###")

            imprint = dict()
            imprint["name"] = metadata.name
            imprint["author"] = metadata.author
            imprint["version"] = self.version
            imprint["tstamp"] = self.tstamp
            for key, value in imprint.iteritems():
                print "\t{0:10}: {1}".format(key, value)

            for script in self.distribution.scripts:
                imprint["script"] = os.path.basename(script).split(".")[0]
                script_copy = script + "~"
                shutil.move(script, script_copy)
                with open(script_copy, "rb") as input:
                    with open(script, "wb+") as output:
                        for line in input:
                            line = imprint_pt.sub("IMPRINT = %s ### imprint ###" % imprint, line, 1)
                            output.write(line)


setup(
    name = "yak",
    version = os.environ.get("version", "3.0.2"),
    description = "process components for enterprise components",

    license = "Apache License Version 2.0",

    author = "exxeleron",
    author_email = "info@exxeleron.com",
    url = "http://www.devnet.de/exxeleron/enterprise-components/",

    cmdclass = {"freeze": bbfreeze,
                "imprint": imprint,
               },
    
    packages = ["components", "osutil", "", "scripts"],
     
    scripts = ["scripts/yak.py"],
    py_modules = [],
    options = {"freeze": dict(data_files = ["scripts/yak_complete_bash.sh"],
                              ),
               },
)
