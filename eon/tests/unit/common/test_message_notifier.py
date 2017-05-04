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
#.

from testtools import TestCase

from eon.common import message_notifier

NOTIFICATIONS = []


class TestNotify(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        message_notifier.notifier = TestNotifier()
        global NOTIFICATIONS
        self.notifications = NOTIFICATIONS = []

    def tearDown(self):
        TestCase.tearDown(self)

    def test_notify_info(self):
        self.context = {}
        self.priority = "INFO"
        self.event_type = 'event.activated'
        self.message = {
            "resource_name": "Test-Resource-1",
            "resource_id": "123"
        }
        message_notifier.notify(
            self.context, self.priority, self.event_type, self.message)
        self.assertEquals([self.message], self.notifications)

    def test_notify_error(self):
        self.context = {}
        self.priority = "ERROR"
        self.event_type = 'event.activated'
        self.message = {
            "resource_name": "Test-Resource-2",
            "resource_id": "123"
        }
        message_notifier.notify(
            self.context, self.priority, self.event_type, self.message)
        self.assertEquals([self.message], self.notifications)


class TestNotifier():

    def __init__(self):
        pass

    def notify_message(self,
                       context,
                       priority=None,
                       event_type=None,
                       message=None):
        global NOTIFICATIONS
        NOTIFICATIONS.append(message)
