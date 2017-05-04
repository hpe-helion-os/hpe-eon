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

import copy
import functools
import logging

import netaddr
from eon.openstack.common import timeutils
from eon.openstack.common import uuidutils
from eon.common import exception
from eon.db.sqlalchemy import models


LOG = logging.getLogger(__name__)

DATA = {
    'vcenters': {},
    'esx_proxys': {},
    'ippools': {},
    'esx_proxy_ips': {},
    'vcenter_properties': {},
    'resource_entity': {}
}


def log_call(func):
    """
    Log function call.
    """
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        """
        Wrapper for called function.
        """
        LOG.info('Calling %(funcname)s: args=%(args)s, kwargs=%(kwargs)s' %
                 {"funcname": func.__name__,
                  "args": args,
                  "kwargs": kwargs})
        output = func(*args, **kwargs)
        LOG.info('Returning %(funcname)s: %(output)s' %
                 {"funcname": func.__name__,
                  "output": output})
        return output
    return wrapped


def reset():
    """
    Empty all DATA values.
    """
    global DATA
    DATA = {
        'vcenters': {},
        'esx_proxys': {},
        'ippools': {},
        'esx_proxy_ips': {},
        'vcenter_properties': {},
        'resource_entity': {}
    }


def setup_db_env(*args, **kwargs):
    """
    Setup global environment configuration variables.

    We have no connection-oriented environment variables, so this is a NOOP.
    """
    pass


def clear_db_env(*args, **kwargs):
    """
    Setup global environment configuration variables.

    We have no connection-oriented environment variables, so this is a NOOP.
    """
    pass


def get_transactional_session(event):
    pass


def commit_session(event, session):
    pass


def rollback_session(event, session):
    pass


def _get_session():
    """
    Get simple session.
    """
    return DATA


def _ippool_format(pool_id, **values):
    """
    Return default ippool data.
    """
    dt = timeutils.utcnow()
    ippool = {
        'id': pool_id,
        'pool_type': None,
        'ips': [],
        'created_at': dt,
        'updated_at': dt,
        'deleted_at': None,
        'deleted': False,
    }
    ippool.update(values)

    return ippool


def _ip_format(ip_id, **values):
    """
    Return default ip data.
    """
    dt = timeutils.utcnow()
    ip = {
        'id': ip_id,
        'ipaddress': None,
        'pool_id': None,
        'esx_proxy_id': None,
        'created_at': dt,
        'updated_at': dt,
        'deleted_at': None,
        'deleted': False,
    }
    ip.update(values)

    return ip


def _esx_proxy_format(esx_proxy_id, **values):
    """Return default esx proxy data"""
    dt = timeutils.utcnow()
    esx_proxy = {'id': esx_proxy_id,
                 'active': None,
                 'name': None,
                 'ip_address': None,
                 'vcenter_id': None,
                 'routing_key': None,
                 'created_at': dt,
                 'updated_at': dt,
                 'deleted_at': None,
                 'deleted': False,
                 }
    esx_proxy.update(values)

    return esx_proxy


def _vcenter_format(vcenter_id, **values):
    """ Returns default vCenter data """
    dt = timeutils.utcnow()
    vcenter = {'id': vcenter_id,
              'name': None,
              'ip_address': None,
              'username': None,
              'password': None,
              'password_id': None,
              'created_at': dt,
              'updated_at': dt,
              'deleted_at': None,
              'deleted': False,
              }
    vcenter.update(values)
    return vcenter


@log_call
def ip_get_all(context, session=None,
               force_show_deleted=False, unassigned=None):
    """
    Return all ip data.
    """
    session = session or _get_session()
    return _ip_get_all(context,
                       session=session,
                       force_show_deleted=force_show_deleted,
                       unassigned=unassigned)


def _ip_get_all(context, session=None, force_show_deleted=False,
                pool_id=None, unassigned=None):
    """Get all esx proxy ips or raise if it does not exist."""
    session = session or _get_session()

    ips = session['esx_proxy_ips'].values()

    if force_show_deleted is not None:
        ips = [x for x in ips if x['deleted'] == force_show_deleted]

    if pool_id:
        ips = [x for x in ips if x['pool_id'] == pool_id]
    if unassigned is False:
        ips = [x for x in ips if x['esx_proxy_id'] is not None]
    elif unassigned:
        ips = [x for x in ips if x['esx_proxy_id'] is None]
    return ips


def _ip_get(ip_id, context=None,
            session=None, force_show_deleted=False):
    """
    Get EsxProxyIP object.
    """
    session = session or _get_session()
    try:
        ip = session['esx_proxy_ips'][ip_id]

    except KeyError:
        msg = (_("No ESX Proxy IP found with ID %s" % ip_id))
        LOG.info(msg)
        raise exception.NotFound(msg)

    if ip['deleted'] and\
            not (force_show_deleted or context.show_deleted):
        msg = (_("No ESX Proxy IP found with ID %s" % ip_id))
        LOG.info(msg)
        raise exception.NotFound(msg)

    return ip


@log_call
def ip_get(context, ip_id, session=None,
           force_show_deleted=False):
    """
    Return ip object of given id
    """
    ip = _ip_get(ip_id,
                 context=context,
                 session=session,
                 force_show_deleted=force_show_deleted)

    return copy.deepcopy(ip)


def _ip_update(values, context=None, session=None, ip_id=None):
    """
    :param context: Request context
    :param values: A dict of attributes to set
    :param ip_id: If None, create the vcenter, otherwise,
        find and update it
    """
    session = session or _get_session()
    if ip_id:
        ip_ref = _ip_get(ip_id, context=context, session=session)
    else:
        ip_id = values.get('id', uuidutils.generate_uuid())
        if ip_id in DATA['esx_proxy_ips']:
            raise exception.Duplicate(_("IP %s already exists!"
                                      % values['ipaddress']))
        ip_ref = _ip_format(ip_id)
    ip_ref.update(**values)
    session['esx_proxy_ips'][ip_id] = ip_ref
    return ip_ref


@log_call
def ip_destroy(context, ip_id):
    """Destroy the ip or raise if it does not exist."""
    session = _get_session()
    ip_ref = _ip_get(ip_id, context=context, session=session)
    ip_ref['deleted'] = True
    return ip_ref


@log_call
def ip_create(context, values, session=None):
    """
    Create EsxProxyIP object.
    """
    ip = _ip_update(values, context=context, session=session)
    return copy.deepcopy(ip)


def ippool_create(context, values):
    """
    Create esx proxy ip pool.

    :param context: Request context
    :param values: A dict of attributes to set
    """
    session = _get_session()

    return _ippool_update(values, context=context, session=session)


def ippool_get(context, pool_id, session=None, force_show_deleted=False):
    """
    Return ippool object of given id
    """
    return _ippool_get(pool_id,
                       context=context,
                       session=session,
                       force_show_deleted=force_show_deleted)


def _ippool_get(pool_id, context=None, session=None, force_show_deleted=False):
    """Get an esx proxy ip pool or raise if it does not exist."""
    session = session or _get_session()

    if pool_id not in session['ippools']:
        msg = (_("No ESX Proxy IP Pool found with ID %s" % pool_id))
        LOG.error(msg)
        raise exception.NotFound(msg)

    ippool_ref = session['ippools'][pool_id]

    if ippool_ref['deleted'] != force_show_deleted:
        msg = (_("No ESX Proxy IP Pool found with ID %s" % pool_id))
        LOG.error(msg)
        raise exception.NotFound(msg)

    return ippool_ref


def _ippool_get_all(context, session=None, force_show_deleted=False):
    """Get all esx proxy ips or raise if it does not exist."""
    session = session or _get_session()

    return session['ippools'].values()


def ip_get_by_pool_id(context, pool_id,
                      session=None, force_show_deleted=False):
    """Get all IP associated with ip pool.

    All ips from ip pool.
    """
    session = session or _get_session()
    return _ip_get_all(context,
                       session=session,
                       force_show_deleted=force_show_deleted,
                       pool_id=pool_id)


def ippool_get_all(context, session=None, force_show_deleted=False):
    """
    Return all ip data.
    """
    session = session or _get_session()
    return _ippool_get_all(context,
                           session=session,
                           force_show_deleted=force_show_deleted)


def _ippool_update(values, context=None, session=None, pool_id=None):
    """
    :param context: Request context
    :param values: A dict of attributes to set
    :param ip_id: If None, create the vcenter, otherwise,
        find and update it
    """
    session = session or _get_session()
    ippools_ref = ippool_get_all(context, session=session)
    esx_proxys = esx_proxy_get_all(context=context)
    # Check is changing pool_type and raise exception
    # if esx proxy already exist.
    if ippools_ref and \
            'pool_type' in values and \
            ippools_ref[0]['pool_type'] != values['pool_type'] and \
            esx_proxys:
        msg = _("Can't change pool type."
                "IP already in use.")
        raise exception.InvalidOperation(msg)

    if pool_id:
        ippool_ref = _ippool_get(pool_id,
                                 context=context,
                                 session=session)
    elif ippools_ref:
        ippool_ref = ippools_ref[0]
    else:
        pool_id = values.get('id', uuidutils.generate_uuid())
        ippool_ref = _ippool_format(pool_id)
    ippool_values = {'pool_type': values['pool_type']}
    ippool_ref.update(ippool_values)

    # Delete all ip if its dhcp
    if ippool_ref['pool_type'] == 'dhcp':
        ip_delete_all(context, session=session)

    ips = []
    for ippool in values['allocation_pools']:
        for esx_ip in netaddr.IPRange(ippool['start'], ippool['end']):
            ip_values = {'ipaddress': str(esx_ip),
                         'pool_id': ippool_ref['id']}
            ips.append(ip_create(context, ip_values, session))
    ippool_ref['ips'] = ips
    session['ippools'][pool_id] = ippool_ref
    return ippool_ref


def ip_delete_all(context, session=None):
    session = session or _get_session()
    used_ips = ip_get_all(context, session, unassigned=False)
    if used_ips:
        msg = _("IP is in use. Can't delete it")
        raise exception.InvalidOperation(msg)
    ips_ref = ip_get_all(context, session=session, force_show_deleted=None)
    for ip_ref in ips_ref:
        del session['esx_proxy_ips'][ip_ref['id']]


def esx_proxy_get_all(context=None, vcenter_id=None, session=None,
                      force_show_deleted=False):
    """Get all esx_proxy or raise if it does not exist."""
    session = session or _get_session()
    return [x for x in session['esx_proxys'].values()
            if x['deleted'] == force_show_deleted]


def esx_proxy_create(context, values, session=None):
    """Create an esx-proxy from the values dictionary."""
    return _esx_proxy_update(context, values, None, False, session=session)


def esx_proxy_update(context, esx_proxy_id, values, purge_props=False,
                     session=None):
    """
    Set the given properties on an esx_proxy and update it.
    :raises NotFound if esx_proxy does not exist.
    """
    return _esx_proxy_update(context, values, esx_proxy_id, purge_props,
                             session=session)


def _esx_proxy_update(context, values, esx_proxy_id, purge_props=False,
                      session=None):
    """
    Used internally by vcenter_create and vcenter_update

    :param context: Request context
    :param values: A dict of attributes to set
    :param vcenter_id: If None, create the vcenter, otherwise,
        find and update it
    """
    session = session or _get_session()
    if esx_proxy_id:
        esx_proxy_ref = _esx_proxy_get(context,
                                       esx_proxy_id,
                                       session=session,
                                       force_show_active_only=False)
    else:
        esx_proxy_id = values.get('id', uuidutils.generate_uuid())
        if esx_proxy_id in DATA['esx_proxys']:
            raise exception.Duplicate("ESX_PROXY ID already exists!")
        esx_proxy_ref = _esx_proxy_format(esx_proxy_id)
    esx_proxy_ref.update(values)
    session['esx_proxys'][esx_proxy_id] = esx_proxy_ref
    return esx_proxy_get(context, esx_proxy_ref['id'],
                         force_show_active_only=False,
                         session=session)


def esx_proxy_get(context, esx_proxy_id, session=None,
                  force_show_deleted=False, force_show_active_only=True):
    esx_proxy = _esx_proxy_get(context, esx_proxy_id, session=session,
                               force_show_deleted=force_show_deleted,
                               force_show_active_only=force_show_active_only)
    return esx_proxy


def _esx_proxy_get(context, esx_proxy_id, session=None,
                   force_show_deleted=False, force_show_active_only=True):
    """Get an esx_proxy or raise if it does not exist."""
    session = session or _get_session()

    if esx_proxy_id not in session['esx_proxys']:
        raise exception.NotFound("No Esx-Proxy found (ID %s)" % esx_proxy_id)

    esx_proxy_ref = session['esx_proxys'][esx_proxy_id]
    if not force_show_deleted and esx_proxy_ref['deleted']:
        raise exception.NotFound("No Esx-Proxy found (ID %s)" % esx_proxy_id)

    if force_show_active_only and not esx_proxy_ref['active']:
        raise exception.NotFound("No Esx-Proxy found (ID %s)" % esx_proxy_id)

    return esx_proxy_ref


def vcenter_get_all(context, session=None, force_show_deleted=False):
    vcenter = _vcenter_get_all(context, session=session)
    return vcenter


def _vcenter_get_all(context, session=None):
    """Get all vcenter or raise if it does not exist."""
    session = session or _get_session()
    return session['vcenters'].values()


def vcenter_create(context, values, session=None):
    """Create an vcenter from the values dictionary."""
    return _vcenter_update(context, values, None, False,
                            session=session)


def vcenter_update(context, vcenter_id, values, purge_props=False,
                    session=None):
    """
    Set the given properties on an vcenter and update it.

    :raises NotFound if vcenter does not exist.
    """
    return _vcenter_update(context, values, vcenter_id, purge_props,
                            session=session)


def _vcenter_update(context, values, vcenter_id, purge_props=False,
                      session=None):

    """ Used internally by vcenter_create and vcenter_update """

    session = session or _get_session()
    if vcenter_id:
        vcenter_ref = _vcenter_get(context, vcenter_id, session=session)
    else:
        vcenter_id = values.get('id', uuidutils.generate_uuid())
        values['id'] = vcenter_id
        vcenter_ref = models.VCenter()
    vcenter_ref.update(values)
    session['vcenters'][vcenter_id] = vcenter_ref

    return vcenter_get(context, vcenter_ref['id'], session=session)


def vcenter_get(context, vcenter_id, session=None, force_show_deleted=False):
    vcenter = _vcenter_get(context, vcenter_id, session=session,
                           force_show_deleted=force_show_deleted)
    return vcenter


def _vcenter_get(context, vcenter_id, session=None, force_show_deleted=False):
    """Get an vcenter or raise if it does not exist."""
    session = session or _get_session()

    if vcenter_id not in session['vcenters']:
        msg = (_("No vCenter found with ID %s" % vcenter_id))
        LOG.error(msg)
        raise exception.NotFound(msg)

    vcenter_ref = session['vcenters'][vcenter_id]
    return vcenter_ref


def vcenter_destroy(context, vcenter_id):
    """Destroy the vcenter or raise if it does not exist."""
    session = _get_session()
    vcenter_ref = _vcenter_get(context, vcenter_id, session=session)
    if vcenter_ref:
            vcenter_ref['deleted'] = True
    return vcenter_ref


def get_property_for_resource(context, resource_id, name, prop_type,
                              session=None):
    """Get an resource_entity or raise if it does not exist."""
    properties_ref = None
    session = session or _get_session()
    if not session:
        value = None
        resource_id = None
        _update_resource_property(context, name, value, resource_id,
                              prop_type='undefined')
    try:
        for x in session['vcenter_properties'].values():
            if (x.resource_id == resource_id and x.name == name):
                properties_ref = x

    except IndexError:
        LOG.debug("No properties found for RESOURCE_ID %s"
            % resource_id)
        return
    return properties_ref


def _update_resource_property(context, name, value, resource_id,
                              prop_type='undefined', session=None):
    """
    Used internally by vcenter_create and vcenter_update
    :param context: Request context
    :param values: A dict of attributes to set
    :param vcenter_id: If None, create the vcenter, otherwise,
        find and update it
    """
    session = session or _get_session()
    property_ref = get_property_for_resource(context, resource_id,
                                             name=name,
                                             prop_type=prop_type,
                                             session=session)
    if not property_ref:
        property_ref = models.VCenterProperty()
    record = dict()
    record['name'] = name
    record['type'] = prop_type
    record['value'] = value
    record['resource_id'] = resource_id
    record['id'] = uuidutils.generate_uuid()
    record['password_id'] = 1

    property_ref.update(record)
    session['vcenter_properties'][record['id']] = property_ref
    return property_ref


def update_resource_properties(context, resource_id, values, session=None):
    """
    Used internally by vcenter_create and vcenter_update
    :param context: Request context
    :param resource_id: Update properties for the resource
    :param values: A dict of attributes to set
    """
    ids = dict()
    for key in values.keys():
        ref = _update_resource_property(context,
                                        key,
                                        values.get(key).get('value'),
                                        resource_id,
                                        values.get(key).get('prop_type'),
                                        session=session)
        ids[key] = ref.id
    return ids


def resource_entity_update(context, res_entity_values, session=None):
    """
    Set the given properties on an resource_entity and update it.

    :raises NotFound if resource_entity does not exist.
    """

    return _resource_entity_update(context, res_entity_values, session=session)


def _resource_entity_update(context, res_entity_values, session=None):
    """
    Used internally by vcenter_create and vcenter_update

    :param context: Request context
    :param res_entity_values: A dict of attributes to set
    """

    session = session or _get_session()
    resource_id = res_entity_values.get('id')

    if(session.get('resource_entity') and (
                session.get('resource_entity').get('resource_id'))):

        res_entity_ref = session['resource_entity'][resource_id]
    else:
        resource_id = res_entity_values.get('id', uuidutils.generate_uuid())
        res_entity_values['id'] = resource_id
        res_entity_ref = models.ResourceEntity()
    res_entity_ref.update(res_entity_values)
    session['resource_entity'][resource_id] = res_entity_ref

    return resource_entity_get(context, res_entity_ref.id)


def resource_entity_get(context, resource_entity_id,
                        session=None):
    resource_entity = _resource_entity_get(context, resource_entity_id,
        session=session)
    return resource_entity


def _resource_entity_get(context, resource_entity_id, session=None):
    """Get an resource_entity or raise if it does not exist."""
    session = session or _get_session()
    if resource_entity_id not in session['resource_entity']:
        msg = (_("No Resource found with ID %s" % resource_entity_id))
        LOG.error(msg)
        raise exception.NotFound(msg)

    res_entity_ref = session['resource_entity'][resource_entity_id]
    return res_entity_ref


def get_all_resource_entities_by_vcenter(context, vcenter_id, session=None,
                                         force_show_deleted=False):
    """Get all resource_entities in a vcenter or raise if it does not exist."""
    session = session or _get_session()
    resources = []
    for resource in session['resource_entity'].values():
        if(resource.vcenter_id == vcenter_id):
            resources.append(resource)

    return resources


def get_properties_for_resource(context, resource_id, session=None):
    """Get an resource_entity or raise if it does not exist."""
    session = session or _get_session()
    properties = []

    for vcenter_property in session['vcenter_properties'].values():
        if (vcenter_property.resource_id == resource_id):
                properties.append(vcenter_property)

    return properties


def get_vsheild_properties(context, vcenter_id, prop_type, session=None):
    session = session or _get_session()
    properties = []
    for vcenter_property in session['vcenter_properties'].values():
            if (vcenter_property.resource_id == vcenter_id and
                        vcenter_property.type == 'credential'):
                properties.append(vcenter_property)
    if(properties.__len__() > 0):
        return properties
    else:
        return None


def resource_entity_get_all_by_esx_proxy(context, esx_proxy_id,
                                session=None, force_show_deleted=False):
    """Gets an resource_entity or raise if it does not exist."""
    session = session or _get_session()
    resources = []
    for resource in session['resource_entity'].values():
        if(resource.esx_proxy_id == esx_proxy_id):
            resources.append(resource)

    return resources


def _delete_all_resource_properties(context, resource_id):
    LOG.debug(("_delete_all_resource_properties %s") % resource_id)
    session = _get_session()

    property_refs = get_properties_for_resource(context, resource_id,
                                                 session=session)
    if property_refs:
        for property_ref in property_refs:
            _delete_resource_property(context, property_ref.name, resource_id,
                                      property_ref.type)


def _delete_resource_property(context, name, resource_id, prop_type):
    LOG.debug(("Method _delete_resource_property %s %s")
              % (resource_id, name))
    session = _get_session()
    property_ref = get_property_for_resource(context, resource_id,
                                                  name=name,
                                                  prop_type=prop_type,
                                                  session=session)
    if property_ref:
        property_ref['deleted'] = True


def delete_resource_properties(context, resource_id, properties=None):
    """
    Used internally by vcenter_create and vcenter_update

    :param context: Request context
    :param resource_id: Update properties for the resource
    :param properties: list of properties to be deleted
                        properties = None means all properties will be deleted
    """
    LOG.debug(("delete_resource_properties %s %s")
              % (resource_id, properties))

    if not properties:
        _delete_all_resource_properties(context, resource_id)
    else:
        for prop in properties:
            _delete_resource_property(context, prop.get('name'),
                                      resource_id,
                                      prop.get('prop_type'))


def resource_entity_destroy(context, resource_entity_id):
    """Destroy the vcenter or raise if it does not exist."""
    session = _get_session()
    resource_entity_ref = _resource_entity_get(context, resource_entity_id,
                                               session=session)
    if resource_entity_ref:
        resource_entity_ref['deleted'] = True
    return resource_entity_ref


def resource_entity_create(context, res_entity_values):
    """Create an Managed-Entity from the res_entity_values dictionary."""
    return _resource_entity_update(context, res_entity_values)


def esx_proxy_destroy(context, esx_proxy_id, force_show_active_only=False):
    """Destroy the esx_proxy or raise if it does not exist."""
    session = _get_session()
    esx_proxy_ref = _esx_proxy_get(
        context, esx_proxy_id, session=session,
        force_show_active_only=force_show_active_only)
    esx_proxy_ref.delete(session=session)
    return esx_proxy_ref
