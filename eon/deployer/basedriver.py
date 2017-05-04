#
# (c) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#


class BaseDriver(object):
    """
    Base class for the various drivers ( compute proxy & network )
    """
    def __init__(self):
        self._create_node = True

    def setup_network(self, data):
        raise NotImplementedError()

    def create(self, data):
        raise NotImplementedError()

    def get_info(self, data):
        raise NotImplementedError()

    def delete(self, data):
        raise NotImplementedError()

    def update(self, data):
        raise NotImplementedError()

    def teardown_network(self, data):
        raise NotImplementedError()
