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

import re
import sys
import traceback

_UNDERSCORER_1 = re.compile(r"(.)([A-Z][a-z]+)")
_UNDERSCORER_2 = re.compile("([a-z0-9])([A-Z])")
CAMEL_CASE = re.compile(r"(?!^)_([a-zA-Z])")



def get_short_exc_info():
    exc_type, exc_value = sys.exc_info()[:2]
    return ("".join(traceback.format_exception_only(exc_type, exc_value))).rstrip()


def get_full_exc_info():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    return ("".join(traceback.format_exception(exc_type, exc_value, exc_traceback))).rstrip()


def to_camel_case(value):
    '''
    Converts string from under_score notation to camelCase.
    @param value:  string to be converted
    @return:  converted string
    '''
    return CAMEL_CASE.sub(lambda m: m.group(1).upper(), value)


def to_underscore(value):
    '''
    Converts string from camelCase to UNDER_SCORE notation.
    @param value:  string to be converted
    @return:  converted string
    '''
    subbed = _UNDERSCORER_1.sub(r"\1_\2", value)
    return _UNDERSCORER_2.sub(r"\1_\2", subbed).replace("__", "_").upper()
