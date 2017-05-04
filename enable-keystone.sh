#! /bin/bash
# This script runs as root
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


function AddKeystoneProps
{
# Creates tenant (admin), user(admin), role(admin), assign a role to user
# Creates a service(eon), endpoint

    ADMIN_NAME=${ADMIN_NAME:-admin}
    ADMIN_PASSWORD=${ADMIN_PASSWORD:-password}
    SERVICE_NAME=${SERVICE_NAME:-eon}
    HOST_IP=%HOST_PUBLIC_IP%

    get_id () {
        echo `$@ | awk '/ id / { print $4 }'`
    }

    ADMIN_TENANT=$(get_id keystone tenant-create --name=$ADMIN_NAME)
    ADMIN_USER=$(get_id keystone user-create --name=$ADMIN_NAME --pass=$ADMIN_PASSWORD --email=admin@example.com)
    ADMIN_ROLE=$(get_id keystone role-create --name=$ADMIN_NAME)
    keystone user-role-add --user_id=$ADMIN_USER --role_id=$ADMIN_ROLE --tenant_id=$ADMIN_TENANT
    SERVICE_ID=$(get_id keystone service-create --name=$SERVICE_NAME --type="ESX_Onboarder" --description="eon_service")
    keystone endpoint-create --service-id=$SERVICE_ID --publicurl=http://$HOST_IP:8282/v2.0 --internalurl=http://localhost:8282/v2.0 --adminurl=http://localhost:35357/v2.0 --region RegionOne
}

function GetTokens
{
# Get tokens
 
    unset OS_SERVICE_TOKEN OS_SERVICE_ENDPOINT

    tok1=$(get_id keystone --os-username=$ADMIN_NAME --os-password=$ADMIN_PASSWORD --os-auth-url=http://localhost:35357/v2.0 token-get)
    AUTH_TOKEN=$(get_id keystone --os-username=$ADMIN_NAME --os-password=$ADMIN_PASSWORD --os-tenant-name=$ADMIN_NAME --os-auth-url=http://localhost:35357/v2.0 token-get)
    echo "X-Auth-Token"
    echo $AUTH_TOKEN
}

function main
{
    AddKeystoneProps;
    GetTokens;
}

main
