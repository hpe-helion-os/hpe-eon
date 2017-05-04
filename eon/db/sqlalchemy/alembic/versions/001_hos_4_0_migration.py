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

"""Migrate eon DB from HOS 3.0 to HOS 4.0
Revision ID: 2ac322d60ab1
Revises: 9382eec1dcab
Create Date: 2016-06-27 20:03:36.102969

"""

import eon.db

from alembic import op
from eon.virt import constants

# revision identifiers, used by Alembic.
revision = '2ac322d60ab1'
down_revision = '9382eec1dcab'

RESOURCE_TABLE = "resource"
NAME_COLUMN = "name"
DELETED_COLUMN = "deleted"

# Ordered specifically to mitigate FOREIGN KEY constraint failure
# during sequential deletion of eon version 1.0 tables
DEPRECATED_TABLES = [
    "resource_entity", "esx_proxy", "vcenters_properties", "vcenters"
]


def upgrade():
    """Upgrade eon DB from HOS 3.0 to HOS 4.0

    1. Create "hypervisor_id" key in the properties table for all the
     activated resources
    2. Remove the unique constraint on (name, deleted) in Resource table
    3. Deletes the unused eon version 1.0 tables
    """
    db_api = eon.db.get_api()
    db_api.setup_db_env()
    activated_resource_ids = _get_resource_ids(
        None, db_api, constants.EON_RESOURCE_STATE_ACTIVATED)
    _create_hypervisor_id(None, db_api, activated_resource_ids)
    _introduce_state_for_res_mgr(None, db_api)
    op.drop_index(NAME_COLUMN, table_name=RESOURCE_TABLE)
    [op.drop_table(table) for table in DEPRECATED_TABLES]


def downgrade():
    """Downgrade eon DB from HOS 4.0 to HOS 3.0

    1. Delete "hypervisor_id" key in the properties table for all the
     activated resource
    2. Create unique constraint on (name, deleted) in Resource table
    """
    db_api = eon.db.get_api()
    db_api.setup_db_env()
    activated_resource_ids = _get_resource_ids(
        None, db_api, constants.EON_RESOURCE_STATE_ACTIVATED)
    _delete_hypervisor_id(None, db_api, activated_resource_ids)
    _remove_state_for_res_mgr(None, db_api)
    op.create_index(NAME_COLUMN, RESOURCE_TABLE,
                    [NAME_COLUMN, DELETED_COLUMN], unique=True)


def _get_resource_ids(context, db_api, state):
    activate_filter = {"state": state}
    return [rsc.id for rsc in db_api.get_all_resources(
        context, **activate_filter)]


def _create_hypervisor_id(context, db_api, id_list):
    hypervisor_id_value = "UNSET"
    [db_api.create_property(context, id_, constants.HYPERVISOR_ID,
                            hypervisor_id_value)
     for id_ in id_list]


def _delete_hypervisor_id(context, db_api, id_list):
    [db_api.delete_property(context, id_, key=constants.HYPERVISOR_ID)
     for id_ in id_list]


def _get_resource_manager_ids(context, db_api):
    return [res_mgrs.id for res_mgrs in
            db_api.get_all_resource_managers(context)]


def _introduce_state_for_res_mgr(context, db_api):
    key_ = constants.RESOURCE_MGR_STATE_KEY
    value_ = constants.EON_RESOURCE_MANAGER_STATE_REGISTERED
    res_mgr_ids = _get_resource_manager_ids(context, db_api)
    [db_api.create_resource_mgr_property(
        context, id_, key=key_, value=value_)
     for id_ in res_mgr_ids]


def _remove_state_for_res_mgr(context, db_api):
    key_ = constants.RESOURCE_MGR_STATE_KEY
    res_mgr_ids = _get_resource_manager_ids(context, db_api)
    [db_api.delete_resource_mgr_property(
        context, id_, key=key_)
     for id_ in res_mgr_ids]
