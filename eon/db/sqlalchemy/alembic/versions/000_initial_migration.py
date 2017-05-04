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

"""Initial migration

Revision ID: 9382eec1dcab
Revises: None
Create Date: 2014-03-22 08:09:54.190892

"""

from eon.db.sqlalchemy import models, api

# revision identifiers, used by Alembic.
revision = '9382eec1dcab'
down_revision = None


def upgrade():
    models.register_models(api.get_engine())


def downgrade():
    raise NotImplementedError(
        'Downgrade from initial migration is unsupported.'
    )
