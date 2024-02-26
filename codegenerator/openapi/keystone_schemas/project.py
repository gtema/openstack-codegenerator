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

from keystone.resource import schema as ks_schema


PROJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        **ks_schema._project_properties,
    },
    "additionalProperties": True,
}

PROJECT_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "project": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                **ks_schema._project_properties,
            },
            "additionalProperties": True,
        },
    },
}

PROJECT_CREATE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"project": copy.deepcopy(ks_schema.project_create)},
}

PROJECT_UPDATE_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"project": copy.deepcopy(ks_schema.project_update)},
}


PROJECTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"projects": {"type": "array", "items": PROJECT_SCHEMA}},
}

PROJECT_LIST_PARAMETERS = {
    "domain_id": {
        "in": "query",
        "name": "domain_id",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "enabled": {
        "in": "query",
        "name": "enabled",
        "description": "If set to true, then only enabled projects will be returned. Any value other than 0 (including no value) will be interpreted as true.",
        "schema": {"type": "boolean"},
    },
    "is_domain": {
        "in": "query",
        "name": "is_domain",
        "description": "If this is specified as true, then only projects acting as a domain are included. Otherwise, only projects that are not acting as a domain are included.",
        "schema": {"type": "boolean"},
        "x-openstack": {"min-ver": "3.6"},
    },
    "name": {
        "in": "query",
        "name": "name",
        "description": "Filters the response by a resource name.",
        "schema": {"type": "string"},
    },
    "parent_id": {
        "in": "query",
        "name": "parent_id",
        "description": "Filters the response by a parent ID.",
        "schema": {"type": "string", "format": "uuid"},
        "x-openstack": {"min-ver": "3.4"},
    },
}
