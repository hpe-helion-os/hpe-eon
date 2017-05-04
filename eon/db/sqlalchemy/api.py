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

import logging
import time

from oslo_config import cfg
import sqlalchemy
from eon.common.gettextutils import _
import eon.common.log as os_logging
import sqlalchemy.orm as sa_orm

from eon.common import exception
from eon.db.sqlalchemy import models


_ENGINE = None
_MAKER = None
_MAX_RETRIES = None
_RETRY_INTERVAL = None
BASE = models.Base
sa_logger = None
LOG = os_logging.getLogger(__name__)


STATUSES = ['active', 'saving', 'queued', 'killed', 'pending_delete',
            'deleted']

db_opts = [
    cfg.IntOpt('sql_idle_timeout', default=3600,
               help=(_('Period in seconds after which SQLAlchemy should '
                       'reestablish its connection to the database.'))),
    cfg.IntOpt('sql_max_retries', default=60,
               help=(_('The number of times to retry a connection to the SQL'
                       'server.'))),
    cfg.IntOpt('sql_retry_interval', default=1,
               help=(_('The amount of time to wait (in seconds) before '
                       'attempting to retry the SQL connection.'))),
    cfg.BoolOpt('db_auto_create', default=False,
                help=(_('A boolean that determines if the database will be '
                        'automatically created.'))),
]

CONF = cfg.CONF
CONF.register_opts(db_opts)
CONF.import_opt('debug', 'eon.common.log')


def setup_db_env():
    """
    Setup configuration for database
    """
    global sa_logger, _IDLE_TIMEOUT, _MAX_RETRIES, _RETRY_INTERVAL, _CONNECTION

    _IDLE_TIMEOUT = CONF.sql_idle_timeout
    _MAX_RETRIES = CONF.sql_max_retries
    _RETRY_INTERVAL = CONF.sql_retry_interval
    _CONNECTION = CONF.esx_sql_connection
    sa_logger = logging.getLogger('sqlalchemy.engine')


def get_transactional_session(event, autocommit=False, expire_on_commit=True):
    """Helper method to grab transaction session"""
    LOG.debug(("%s: Acquiring DB Session.") % event)
    session = _get_session(autocommit=autocommit,
                           expire_on_commit=expire_on_commit,
                           transactional=True)
    LOG.debug(("%s: DB Session acquired.") % event)
    return session


def commit_session(event, session):
    """Helper method to commit transactional session"""
    if not session:
        LOG.debug("No session provided.")
        return
    LOG.debug(("%s: DB commit initiated") % event)
    session.commit()
    LOG.debug(("%s: DB commit successfull.") % event)


def rollback_session(event, session):
    if not session:
        LOG.debug("No session provided.")
        return
    LOG.error(("%s: DB rollback initiated.") % event)
    session.rollback()
    LOG.error(("%s: DB rollback completed.") % event)


def _get_session(autocommit=True, expire_on_commit=False, transactional=False):
    """Helper method to grab session"""
    if not transactional:
        global _MAKER
        if not _MAKER:
            get_engine()
            _get_maker(autocommit, expire_on_commit)
            assert(_MAKER)
        session = _MAKER()
    else:
        get_engine()
        _maker = _get_maker(autocommit, expire_on_commit,
                            transactional=transactional)
        assert(_maker)
        session = _maker()
    return session


def get_engine():
    """Return a SQLAlchemy engine.
       May assign _ENGINE if not already assigned
    """
    global _ENGINE, sa_logger, _CONNECTION, _IDLE_TIMEOUT, _MAX_RETRIES,\
        _RETRY_INTERVAL

    if not _ENGINE:
        sqlalchemy.engine.url.make_url(_CONNECTION)

        engine_args = {
            'pool_recycle': _IDLE_TIMEOUT,
            'echo': False,
            'convert_unicode': True}

        try:
            _ENGINE = sqlalchemy.create_engine(_CONNECTION, **engine_args)
            _ENGINE.connect = _wrap_db_error(_ENGINE.connect)
            _ENGINE.connect()
        except Exception as err:
            msg = (("Error configuring registry database with supplied "
                     "sql_connection. Got error: %s") % err)
            LOG.error(msg)
            raise

        sa_logger = logging.getLogger('sqlalchemy.engine')

    return _ENGINE


def _get_maker(autocommit=True, expire_on_commit=False, transactional=False):
    """
    Return a SQLAlchemy sessionmaker,
    May assign __MAKER if not already assigned
    """
    global _MAKER, _ENGINE
    assert _ENGINE
    if transactional:
        return sa_orm.sessionmaker(bind=_ENGINE,
                                   autocommit=autocommit,
                                   expire_on_commit=expire_on_commit)
    if not _MAKER:
        _MAKER = sa_orm.sessionmaker(bind=_ENGINE,
                                     autocommit=autocommit,
                                     expire_on_commit=expire_on_commit)
    return _MAKER


def _is_db_connection_error(args):
    """Return True if error in connecting to db."""
    # NOTE(adam_g): This is currently MySQL specific and needs to be extended
    #               to support Postgres and others.
    conn_err_codes = ('2002', '2003', '2006')
    for err_code in conn_err_codes:
        if args.find(err_code) != -1:
            return True
    return False


def _wrap_db_error(f):
    """Retry DB connection. Copied from nova and modified."""
    def _wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlalchemy.exc.OperationalError as e:
            if not _is_db_connection_error(e.args[0]):
                raise

            remaining_attempts = _MAX_RETRIES
            while True:
                LOG.warning(("SQL connection failed. %d attempts left."),
                            remaining_attempts)
                remaining_attempts -= 1
                time.sleep(_RETRY_INTERVAL)
                try:
                    return f(*args, **kwargs)
                except sqlalchemy.exc.OperationalError as e:
                    if (remaining_attempts == 0 or
                            not _is_db_connection_error(e.args[0])):
                        raise
                except sqlalchemy.exc.DBAPIError:
                    raise
        except sqlalchemy.exc.DBAPIError:
            raise
    _wrap.func_name = f.func_name
    return _wrap


def handle_db_exception(fn):
    """Helper to handle exception gracefully"""
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except sqlalchemy.exc.IntegrityError as e:
            if ("Duplicate entry ") in e.message:
                raise exception.Duplicate()
            else:
                raise e
        except (sa_orm.exc.NoResultFound, exception.NotFound,
                exception.Duplicate,
                exception.InvalidOperation,
                exception.DatabaseMigrationError) as e:
            raise e
        except Exception as e:
            LOG.exception(e)
            LOG.error("Unexpected database error occurred: %s" % e)
            raise exception.UnexpectedDBException(reason=e.message)
    return wrapped

# Resource Managers DB API


def get_all_resource_managers(context, session=None, **kwargs):
    """Get all Resource Managers from resource_manager table

    :param kwargs: Optional field to filter based on type (or) name (or) state
     Ex:
        {
         'type' : 'vcenter',
         'name' : 'vcenter-1',
        }
    :return: List of resource_manger objects
    """
    session = session or _get_session()
    return _get_all(context, session, models.ResourceManager, **kwargs)


def get_resource_manager(context, _id, session=None):
    """Get a Resource Manager from resource_manager table

    :param _id: ID of the Resource Manager
    :return: resource_manager object
    """
    session = session or _get_session()
    return _get(context, _id, session, models.ResourceManager)


def create_resource_manager(context, values, session=None):
    """Create a Resource Manager in resource_manager table

    :param values: Dictionary to persist in the resource_manger table
    Ex:
        {
         'name': 'vcenter-1',
         'ip_address': '10.1.1.20',
         'username': 'admin',
         'password': 'pass',
         'port': '443',
         'type': 'vcenter'
        }
    :return: created resource_manger object
    """
    session = session or _get_session()
    return _update(context, None, values, session, models.ResourceManager)


def update_resource_manager(context, _id, values, session=None):
    """Update a Resource Manager in resource_manager table

    :param _id: ID of the Resource Manager
    :param values: Dictionary content to persist in the resource_manager table
    Ex:
        {
         'name': 'vcenter-2',
         'ip_address': '10.1.1.20',
         'username': 'admin',
         'password': 'pass',
         'port': '9443',
         'type': 'vcenter'
        }
    :return: updated resource_manager object
    """
    session = session or _get_session()
    return _update(context, _id, values, session, models.ResourceManager)


def delete_resource_manager(context, _id, session=None):
    """Delete a Resource Manager from resource_manager table

    :param _id: ID of the Resource Manager
    :return: deleted resource_manager object
    """
    session = session or _get_session()
    return _delete(context, _id, session, models.ResourceManager)


# Resource DB API

def get_all_resources(context, session=None, **kwargs):
    """Get all Resources from resource table

    :param kwargs: Optional field to filter based on type (or) name
     (or) state (or) resource_mgr_id
     Ex:
        {
         'type' : 'esx_cluster',
         'name' : 'Cluster1',
         'state': 'imported',
         'resource_mgr_id': '305ff8ea-15ee-4401-ab1e-ff12623986de'
        }
    :return: List of resource objects
    """
    session = session or _get_session()
    return _get_all(context, session, models.Resource, **kwargs)


def get_resource(context, _id, session=None):
    """Get a Resource from resource table

    :param _id: ID of the Resource
    :return: resource object
    """
    session = session or _get_session()
    return _get(context, _id, session, models.Resource)


@handle_db_exception
def get_resource_managers_by_resource_id(context, _id, session=None):
    """Get a Resource Mgr from resource Mgr table
    :param _id: ID of the Resource
    :return: resource object
    """
    res = models.Resource
    res_mgr = models.ResourceManager
    session = session or _get_session()
    with session.begin():
        q = session.query(res_mgr).join(res).\
                filter(res.id == _id).\
                filter(res_mgr.id == res.resource_mgr_id)
        return q.one()


def create_resource(context, values, session=None):
    """Create a Resource in resource table

    :param values: Dictionary content to persist in the resource table
    Ex: ESX Cluster
        {
         'name': 'Cluster2',
         'type': 'esx_cluster',
         'state': 'imported',
         'resource_mgr_id': '305ff8ea-15ee-4401-ab1e-ff12623986de''
        }
    Ex: RHEL KVM
        {
         'name': 'Rhel1',
         'type': 'rhel',
         'state': 'imported',
         'ip_address': '10.1.2.20',
         'username': 'admin',
         'password': 'pass'
        }
    :return: created resource object
    """
    session = session or _get_session()
    return _update(context, None, values, session, models.Resource)


def update_resource(context, _id, values, session=None):
    """Update a Resource in resource table

    :param _id: ID of the Resource
    :param values: Dictionary content to persist in the resource table
    Ex: ESX Cluster
        {
         'name': 'Cluster2',
         'type': 'esx_cluster',
         'state': 'provisioned',
         'resource_mgr_id': '305ff8ea-15ee-4401-ab1e-ff12623986de''
        }
    Ex: RHEL KVM
        {
         'name': 'Rhel2',
         'type': 'rhel',
         'state': 'imported',
         'ip_address': '10.1.2.30',
         'username': 'admin',
         'password': 'pass'
        }
    :return: updated resource object
    """
    session = session or _get_session()
    return _update(context, _id, values, session, models.Resource)


def delete_resource(context, _id, session=None):
    """Delete a Resource from resource table

    :param _id: ID of the Resource
    :return: deleted resource object
    """
    session = session or _get_session()
    return _delete(context, _id, session, models.Resource)


@handle_db_exception
def _get(context, _id, session, db_model):
    with session.begin(subtransactions=True):
        try:
            query = session.query(db_model).filter_by(id=_id)
            instance = query.one()
            return instance
        except sa_orm.exc.NoResultFound:
            msg = _("No %s found with ID %s") % (db_model.__tablename__, _id)
            log_msg = ("No %s found with ID %s") % (db_model.__tablename__,
                       _id)
            LOG.error(log_msg)
            raise exception.NotFound(msg)


@handle_db_exception
def _get_all(context, session, db_model, **kwargs):
    type_ = kwargs.get('type')
    name = kwargs.get('name')
    rsc_mgr_id = kwargs.get('resource_mgr_id')
    state = kwargs.get('state')
    filters = []
    with session.begin(subtransactions=True):
        if type_:
            filters.append(db_model.type == type_)
        if name:
            filters.append(db_model.name == name)
        if rsc_mgr_id:
            filters.append(db_model.resource_mgr_id == rsc_mgr_id)
        if state:
            filters.append(db_model.state == state)
        query = (session.query(db_model).filter(*filters).
                 filter_by(deleted=False))
        instances = query.all()
        if len(instances) == 0:
            LOG.info("No %s found"
                     % db_model.__tablename__)
        return instances


@handle_db_exception
def _update(context, _id, values, session, db_model):
    with session.begin(subtransactions=True):
        if db_model.__tablename__ == 'resource_manager':
            table_ref = (get_resource_manager(context, _id, session=session)
                         if _id else models.ResourceManager())
        elif db_model.__tablename__ == 'resource':
            table_ref = (get_resource(context, _id, session=session)
                         if _id else models.Resource())
        table_ref.update(values)
        table_ref.save(session=session)
    return table_ref


@handle_db_exception
def _delete(context, _id, session, db_model):
    with session.begin(subtransactions=True):
        if db_model.__tablename__ == 'resource_manager':
            table_ref = get_resource_manager(context, _id, session=session)
        elif db_model.__tablename__ == 'resource':
            table_ref = get_resource(context, _id, session=session)
        table_ref.delete(session=session)
    return table_ref

# Properties DB API methods


@handle_db_exception
def get_properties(context, parent_id, key=None, session=None):
    """Get properties from the properties table for a Resource

    :param parent_id: ID of the Resource
    :param key: key of the property. When not specified returns all the
     properties associated with parent_id
    :return: List of property objects
    """
    session = session or _get_session()
    with session.begin(subtransactions=True):
        try:
            if key:
                query = (session.query(models.Properties).
                         filter_by(parent_id=parent_id).
                         filter_by(key=key).filter_by(deleted=False))
                prop = query.one()
                return [prop]
            else:
                query = (session.query(models.Properties).
                         filter_by(parent_id=parent_id).
                         filter_by(deleted=False))
                props = query.all()
                return props
        except sa_orm.exc.NoResultFound:
            msg = _("No Property found for Parent ID %s") % parent_id
            log_msg = ("No Property found for Parent ID %s") % parent_id
            LOG.error(log_msg)
            raise exception.NotFound(msg)


def create_property(context, parent_id, key, value, session=None):
    """Create a property in properties table for a Resource

    :param parent_id: ID of the Resource
    :param key: key of the property
    :param value: value for the key
    :return: created property object
    """
    session = session or _get_session()
    return _update_property(context, None, parent_id, key, value,
                            session=session)


def update_property(context, _id, parent_id, key, value, session=None):
    """Update a property in properties table for a Resource

    :param _id: ID of the Property
    :param parent_id: ID of the Resource
    :param key: key of the property
    :param value: new value for the key
    :return: updated property object
    """
    session = session or _get_session()
    return _update_property(context, _id, parent_id, key, value,
                            session=session)


@handle_db_exception
def _update_property(context, _id, parent_id, key, value, session):
    with session.begin(subtransactions=True):
        if _id:
            prop_ref = get_properties(context, parent_id, key=key,
                                      session=session)[0]
        else:
            prop_ref = models.Properties()
        prop_ref.update({'parent_id': parent_id,
                         'key': key,
                         'value': value})
        prop_ref.save(session=session)
    return get_properties(context, prop_ref.parent_id, key=key,
                          session=session)[0]


@handle_db_exception
def delete_property(context, parent_id, key=None, session=None):
    """Delete a property from properties table for a Resource

    :param parent_id: ID of the Resource
    :param key: key of the property. When not specified deletes all the
     properties associated with parent_id
    :return: List of deleted property objects
    """
    session = session or _get_session()
    with session.begin(subtransactions=True):
        prop_refs = get_properties(context, parent_id, key=key,
                                   session=session)
        for prop_ref in prop_refs:
            prop_ref.delete(session=session)
        return prop_refs

# Resource Manager Properties DB API methods


@handle_db_exception
def get_resource_mgr_properties(context, parent_id, key=None,
                                    session=None):
    """Get properties from the properties table for a Resource Manager

    :param parent_id: ID of the Resource Managers
    :param key: key of the property. When not specified returns all the
     properties associated with parent_id
    :return: List of property objects
    """
    session = session or _get_session()
    with session.begin(subtransactions=True):
        try:
            if key:
                query = (session.query(models.ResourceManagerProperties).
                         filter_by(parent_id=parent_id).
                         filter_by(key=key).filter_by(deleted=False))
                prop = query.one()
                return [prop]
            else:
                query = (session.query(models.ResourceManagerProperties).
                         filter_by(parent_id=parent_id).
                         filter_by(deleted=False))
                props = query.all()
                return props
        except sa_orm.exc.NoResultFound:
            msg = _("No Property found for Parent ID %s") % parent_id
            log_msg = ("No Property found for Parent ID %s") % parent_id
            LOG.error(log_msg)
            raise exception.NotFound(msg)


def create_resource_mgr_property(context, parent_id, key, value, session=None):
    """Create a property in properties table for a Resource Manager

    :param parent_id: ID of the Resource Manager
    :param key: key of the property
    :param value: value for the key
    :return: created property object
    """
    session = session or _get_session()
    return _update_res_mgr_property(context, None, parent_id, key, value,
                                    session=session)


@handle_db_exception
def _update_res_mgr_property(context, _id, parent_id, key,
                             value, session):
    with session.begin(subtransactions=True):
        if _id:
            prop_ref = get_resource_mgr_properties(context, parent_id,
                                                   key=key,
                                                   session=session)[0]
        else:
            prop_ref = models.ResourceManagerProperties()
        prop_ref.update({'parent_id': parent_id,
                         'key': key,
                         'value': value})
        prop_ref.save(session=session)
    return get_resource_mgr_properties(context, prop_ref.parent_id, key=key,
                                       session=session)[0]


def update_resource_mgr_property(context, _id, parent_id, key, value,
                                 session=None):
    """Update a property in properties table for a Resource

    :param _id: ID of the Property
    :param parent_id: ID of the Resource Manager
    :param key: key of the property
    :param value: new value for the key
    :return: updated property object
    """
    session = session or _get_session()
    return _update_res_mgr_property(context, _id, parent_id, key, value,
                            session=session)


@handle_db_exception
def delete_resource_mgr_property(context, parent_id, key=None, session=None):
    """Delete a property from properties table for a Resource Manager

    :param parent_id: ID of the Resource Manager
    :param key: key of the property. When not specified deletes all the
     properties associated with parent_id
    :return: List of deleted property objects
    """
    session = session or _get_session()
    with session.begin(subtransactions=True):
        prop_refs = get_resource_mgr_properties(context, parent_id, key=key,
                                   session=session)
        for prop_ref in prop_refs:
            prop_ref.delete(session=session)
        return prop_refs
