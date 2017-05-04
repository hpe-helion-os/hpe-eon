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

import eon.db
from eon.common import exception
from eon.virt.baremetal import constants as bm_consts
from eon.virt.baremetal.validator import BaremetalValidator
from eon.openstack.common import log as logging
from eon.virt import constants
from eon.virt import driver


LOG = logging.getLogger(__name__)


class BaremetalDriver(driver.ResourceDriver):

    def __init__(self):
        self.db_api = eon.db.get_api()
        self.db_api.setup_db_env()

    def validate_create(self, context, create_data):
        validator = BaremetalValidator(create_data)
        validator.validate_ilo_details()
        # Add state to IMPORTED
        create_data[constants.EON_RESOURCE_STATE] = (
            constants.EON_RESOURCE_STATE_IMPORTED)
        return create_data

    def get_properties(self, data):
        properties = {}
        for prop in bm_consts.SERVER_PROPERTIES:
            if prop in data.keys():
                properties[prop] = data.get(prop, None)
        return properties

    def validate_update(self, context, db_resource_data, update_data):
        validator = BaremetalValidator(update_data)
        validator.validate_ilo_details()

        properties = self.get_properties(update_data)
        for pkey, pval in properties.iteritems():
            self.db_api.update_property(context, "update_prop",
                                        db_resource_data['id'],
                                        pkey, pval)
        return update_data

    def validate_delete(self, data):
        state = data.get(constants.EON_RESOURCE_STATE)
        allowed_states = [constants.EON_RESOURCE_STATE_IMPORTED,
                          constants.EON_RESOURCE_STATE_REMOVED]
        if state not in allowed_states:
            raise exception.InvalidStateError(observed=state,
                                              expected=allowed_states)
