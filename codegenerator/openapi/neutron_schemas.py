#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
import copy

"""Mapping of the Requests to required fields list

Neutron API defitnitions have no clear way on how to detect required fields in
the request. This mapping is adding such information.
"""
REQUIRED_FIELDS_MAPPING = {
    "SubnetsCreateRequest": ["network_id", "ip_version"],
    "FloatingipsCreateRequest": ["floating_network_id"],
    "FloatingipsUpdateRequest": ["port_id"],
}

EXTENSION_SCHEMA = {
    "type": "object",
    "properties": {
        "alias": {
            "type": "string",
            "description": "A short name by which this extension is also known.",
        },
        "description": {
            "type": "string",
            "description": "Text describing this extension’s purpose.",
        },
        "name": {"type": "string", "description": "Name of the extension."},
        "namespace": {
            "type": "string",
            "description": "A URL pointing to the namespace for this extension.",
        },
        "updated": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the resource was updated.",
        },
    },
}

QUOTA_SCHEMA = {
    "type": "object",
    "properties": {
        "floatingip": {
            "type": "integer",
            "description": "The number of floating IP addresses allowed for each project. A value of -1 means no limit.",
        },
        "network": {
            "type": "integer",
            "description": "The number of networks allowed for each project. A value of -1 means no limit.",
        },
        "port": {
            "type": "integer",
            "description": "The number of ports allowed for each project. A value of -1 means no limit.",
        },
        "rbac_policy": {
            "type": "integer",
            "description": "The number of role-based access control (RBAC) policies for each project. A value of -1 means no limit.",
        },
        "router": {
            "type": "integer",
            "description": "The number of routers allowed for each project. A value of -1 means no limit.",
        },
        "security_group": {
            "type": "integer",
            "description": "The number of security groups allowed for each project. A value of -1 means no limit.",
        },
        "security_group_rule": {
            "type": "integer",
            "description": "The number of security group rules allowed for each project. A value of -1 means no limit.",
        },
        "subnet": {
            "type": "integer",
            "description": "The number of subnets allowed for each project. A value of -1 means no limit.",
        },
        "subnetpool": {
            "type": "integer",
            "description": "The number of subnet pools allowed for each project. A value of -1 means no limit.",
        },
        "project_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the project.",
        },
    },
}


QUOTA_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "used": {"type": "integer", "description": "Used quota"},
        "limit": {"type": "integer", "description": "Current quota limit"},
        "reserved": {"type": "integer", "description": "Reserved quota"},
    },
}


QUOTA_DETAILS_SCHEMA = {
    "type": "object",
    "properties": {
        "floatingip": {
            "description": "The number of floating IP addresses allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "network": {
            "description": "The number of networks allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "port": {
            "description": "The number of ports allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "rbac_policy": {
            "description": "The number of role-based access control (RBAC) policies for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "router": {
            "description": "The number of routers allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "security_group": {
            "description": "The number of security groups allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "security_group_rule": {
            "description": "The number of security group rules allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "subnet": {
            "description": "The number of subnets allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
        "subnetpool": {
            "description": "The number of subnet pools allowed for each project.",
            **copy.deepcopy(QUOTA_DETAIL_SCHEMA),
        },
    },
}
