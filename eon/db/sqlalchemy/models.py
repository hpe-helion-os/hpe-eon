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

from eon.openstack.common import uuidutils
from oslo_db.sqlalchemy import models

from sqlalchemy import Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, UniqueConstraint


class EonBase(models.ModelBase, models.TimestampMixin, models.SoftDeleteMixin):
    """Base class for Eon DB Models inherited from oslo db models"""
    __table_args__ = {'mysql_engine': 'InnoDB'}
    __protected_attributes__ = set(["created_at", "updated_at",
                                    "deleted_at", "deleted"])

    def save(self, session=None):
        from eon.db.sqlalchemy import api
        if session is None:
            session = api._get_session()

        super(EonBase, self).save(session=session)

    def delete(self, session=None):
        from eon.db.sqlalchemy import api
        if not session:
            session = api._get_session()

        session.delete(self)
        session.flush()

    def to_dict(self):
        d = self.__dict__.copy()
        d.pop("_sa_instance_state")
        return d


Base = declarative_base(cls=EonBase)


class ResourceManager(Base):
    """Represent a Resource manager"""
    __tablename__ = 'resource_manager'
    __table_args__ = (UniqueConstraint(
        'name', 'deleted'), {})

    id = Column(String(36), primary_key=True, default=uuidutils.generate_uuid)
    name = Column(String(255), nullable=False)
    ip_address = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    port = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)


class Resource(Base):
    """Represent a Resource"""
    __tablename__ = 'resource'

    id = Column(String(36), primary_key=True, default=uuidutils.generate_uuid)
    name = Column(String(255), nullable=False)
    resource_mgr_id = Column(String(255),
                             ForeignKey('resource_manager.id',
                                        ondelete="CASCADE"),
                             nullable=True)
    ip_address = Column(String(255))
    username = Column(String(255))
    password = Column(String(255))
    type = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    port = Column(String(255), nullable=False)


class Properties(Base):
    """Represent a Property for a Resource
     or HLM resources"""
    __tablename__ = 'properties'
    __table_args__ = (UniqueConstraint('id', name='uniq_properties0id'), {})
    __table_args__ = (UniqueConstraint('key', 'parent_id'), {})

    id = Column(String(36), primary_key=True, default=uuidutils.generate_uuid)
    parent_id = Column(String(255),
                       ForeignKey('resource.id', ondelete="CASCADE"),
                       nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text)


class ResourceManagerProperties(Base):
    """Represent a Property for Resource manager """
    __tablename__ = 'resource_mgr_properties'
    __table_args__ = (UniqueConstraint('id', name='uniq_properties0id'), {})
    __table_args__ = (UniqueConstraint('key', 'parent_id'), {})

    id = Column(String(36), primary_key=True, default=uuidutils.generate_uuid)
    parent_id = Column(String(255),
                       ForeignKey('resource_manager.id', ondelete="CASCADE"),
                       nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text)


def register_models(engine):
    """Registers models with the given engine"""
    models_set = (ResourceManager, Resource, ResourceManagerProperties,
                  Properties)
    for model in models_set:
        model.metadata.create_all(engine)


def unregister_models(engine):
    """Unregisters models with the given engine"""
    models_set = (ResourceManager, Resource, ResourceManagerProperties,
                  Properties)
    for model in models_set:
        model.metadata.drop_all(engine)
