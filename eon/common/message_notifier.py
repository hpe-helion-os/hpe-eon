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

"""Classes to notify messages on to  rabbitmq """

import eon.common.log as logging
from oslo_config import cfg
import oslo_messaging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

notifier_opts = [cfg.ListOpt('eon_notifier_topics',
                             default=[],
                             help='List of rabbitmq topics'
                             ' that EON wants to notify the messages')]

cfg.CONF.register_opts(notifier_opts)

EVENT_TYPE = {}
EVENT_TYPE['activating'] = "eon.resource.activation.start"
EVENT_TYPE['activated'] = "eon.resource.activation.end"
EVENT_TYPE['deactivating'] = "eon.resource.deactivation.start"
EVENT_TYPE['deactivated'] = "eon.resource.deactivation.end"
EVENT_TYPE['removed'] = "eon.resource.removed"


EVENT_PRIORITY_INFO = "INFO"
EVENT_PRIORITY_ERROR = "ERROR"

notifier = None


class OsloMessageNotifier:

    def __init__(self):
        self._topics = CONF.eon_notifier_topics
        self._publisher_id = "eon"
        self._driver = 'messaging'
        self._transport = oslo_messaging.get_transport(cfg.CONF)
        self._notifiers = self._initialize_notifiers()

    def _format_msg(self, msg):
        message = {}
        message['payload'] = msg
        return message

    def _initialize_notifiers(self):
        notifiers = {}
        for topic in self._topics:
            notifier = oslo_messaging.Notifier(self._transport,
                                               driver=self._driver,
                                               publisher_id=self._publisher_id,
                                               topic=topic)
            notifiers[topic] = notifier
        return notifiers

    def notify_message(self,
                       context,
                       priority=None,
                       event_type=None,
                       message=None):
        """
        Message format :
            {'message_id': six.text_type(uuid.uuid4()),
             'publisher_id': 'compute.host1',
             'timestamp': timeutils.utcnow(),
             'priority': 'WARN',
             'event_type': 'compute.create_instance',
             'payload': {'instance_id': 12, ... }}
        """
        for topic in self._notifiers:
            if priority == EVENT_PRIORITY_INFO:
                self._notifiers[topic].info({},
                                            event_type,
                                            self._format_msg(message))
            elif priority == EVENT_PRIORITY_ERROR:
                self._notifiers[topic].error({},
                                             event_type,
                                             self._format_msg(message))
        return


def notify(context, priority, event_type, message):
    """
    Notify message should be called only from here !!
    """
    global notifier
    if notifier is None:
        notifier = OsloMessageNotifier()

    return notifier.notify_message(context, priority, event_type, message)
