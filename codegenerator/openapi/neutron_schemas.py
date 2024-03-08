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

from typing import Any

from codegenerator.common.schema import TypeSchema


"""Mapping of the Requests to required fields list

Neutron API defitnitions have no clear way on how to detect required fields in
the request. This mapping is adding such information.
"""
REQUIRED_FIELDS_MAPPING: dict[str, Any] = {
    "SubnetsCreateRequest": ["network_id", "ip_version"],
    "FloatingipsCreateRequest": ["floating_network_id"],
    "FloatingipsUpdateRequest": ["port_id"],
}

EXTENSION_SCHEMA: dict[str, Any] = {
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

QUOTA_SCHEMA: dict[str, Any] = {
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


QUOTA_DETAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "used": {"type": "integer", "description": "Used quota"},
        "limit": {"type": "integer", "description": "Current quota limit"},
        "reserved": {"type": "integer", "description": "Reserved quota"},
    },
}


QUOTA_DETAILS_SCHEMA: dict[str, Any] = {
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

ROUTER_UPDATE_INTERFACE_REQUEST_SCHEMA: dict[str, Any] = {
    "description": "Request body",
    "type": "object",
    "properties": {
        "subnet_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the subnet. One of subnet_id or port_id must be specified.",
        },
        "port_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the port. One of subnet_id or port_id must be specified.",
        },
    },
    "oneOf": [
        {"required": ["subnet_id"]},
        {"required": ["port_id"]},
    ],
}

ROUTER_INTERFACE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the router.",
        },
        "subnet_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the subnet which the router interface belongs to.",
        },
        "subnet_ids": {
            "type": "array",
            "description": "A list of the ID of the subnet which the router interface belongs to. The list contains only one member.",
            "items": {
                "type": "string",
                "format": "uuid",
            },
            "minItems": 1,
            "maxItems": 1,
        },
        "tenant_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the project who owns the router interface.",
        },
        "project_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the project who owns the router interface.",
        },
        "port_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the port which represents the router interface.",
        },
        "network_id": {
            "type": "string",
            "format": "uuid",
            "description": "Network ID which the router interface is connected to.",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The list of tags on the resource.",
        },
    },
}

ROUTER_UPDATE_EXTRAROUTES_REQUEST_SCHEMA: dict[str, Any] = {
    "description": "Request body",
    "type": "object",
    "properties": {
        "router": {
            "type": "object",
            "properties": {
                "routes": {
                    "type": "array",
                    "description": "The extra routes configuration for L3 router. A list of dictionaries with destination and nexthop parameters. It is available when extraroute extension is enabled.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                            },
                            "nexthop": {
                                "type": "string",
                                "oneOf": [
                                    {
                                        "format": "ipv4",
                                    },
                                    {
                                        "format": "ipv6",
                                    },
                                ],
                            },
                        },
                    },
                },
            },
        }
    },
}

ROUTER_EXTRAROUTES_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "router": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The ID of the router.",
                },
                "name": {
                    "type": "string",
                    "format": "uuid",
                    "description": "The name of the router.",
                },
                "routes": {
                    "type": "array",
                    "description": "The extra routes configuration for L3 router. A list of dictionaries with destination and nexthop parameters. It is available when extraroute extension is enabled.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "destination": {
                                "type": "string",
                            },
                            "nexthop": {
                                "type": "string",
                                "oneOf": [
                                    {
                                        "format": "ipv4",
                                    },
                                    {
                                        "format": "ipv6",
                                    },
                                ],
                            },
                        },
                    },
                },
            },
        }
    },
}


def _get_schema_ref(
    openapi_spec,
    name,
    description=None,
    schema_def=None,
) -> tuple[str | None, str | None, bool]:
    mime_type: str = "application/json"
    ref: str
    if name in [
        "RoutersAdd_Router_InterfaceAdd_Router_InterfaceRequest",
        "RoutersRemove_Router_InterfaceRemove_Router_InterfaceRequest",
    ]:
        openapi_spec.components.schemas[name] = TypeSchema(
            **ROUTER_UPDATE_INTERFACE_REQUEST_SCHEMA
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "RoutersAdd_Router_InterfaceAdd_Router_InterfaceResponse",
        "RoutersRemove_Router_InterfaceRemove_Router_InterfaceResponse",
    ]:
        openapi_spec.components.schemas[name] = TypeSchema(
            **ROUTER_INTERFACE_RESPONSE_SCHEMA
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "RoutersAdd_ExtraroutesAdd_ExtraroutesRequest",
        "RoutersRemove_ExtraroutesRemove_ExtraroutesRequest",
    ]:
        openapi_spec.components.schemas[name] = TypeSchema(
            **ROUTER_UPDATE_EXTRAROUTES_REQUEST_SCHEMA
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "RoutersAdd_ExtraroutesAdd_ExtraroutesResponse",
        "RoutersRemove_ExtraroutesRemove_ExtraroutesResponse",
    ]:
        openapi_spec.components.schemas[name] = TypeSchema(
            **ROUTER_EXTRAROUTES_RESPONSE_SCHEMA
        )
        ref = f"#/components/schemas/{name}"
    else:
        return (None, None, False)

    return (ref, mime_type, True)
