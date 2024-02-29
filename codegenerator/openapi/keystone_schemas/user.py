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
from typing import Any

from keystone.identity import schema as identity_schema

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import TypeSchema


USER_LIST_PARAMETERS: dict[str, Any] = {
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
    "idp_id": {
        "in": "query",
        "name": "idp_id",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "name": {
        "in": "query",
        "name": "name",
        "description": "Filters the response by a resource name.",
        "schema": {"type": "string"},
    },
    "password_expires_at": {
        "in": "query",
        "name": "password_expires_at",
        "description": "Filter results based on which user passwords have expired. The query should include an operator and a timestamp with a colon (:) separating the two, for example: `password_expires_at={operator}:{timestamp}`.\nValid operators are: `lt`, `lte`, `gt`, `gte`, `eq`, and `neq`.\nValid timestamps are of the form: YYYY-MM-DDTHH:mm:ssZ.",
        "schema": {"type": "string", "format": "date-time"},
    },
    "protocol_id": {
        "in": "query",
        "name": "protocol_id",
        "description": "Filters the response by a protocol ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "unique_id": {
        "in": "query",
        "name": "unique_id",
        "description": "Filters the response by a unique ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
}


USER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid", "readOnly": True},
        **identity_schema._user_properties,
    },
}

USER_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"user": identity_schema.user_create},
}

USER_PATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"user": identity_schema.user_update},
}


USER_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"user": USER_SCHEMA},
}

USERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"users": {"type": "array", "items": USER_SCHEMA}},
}

USER_PWD_CHANGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"user": identity_schema.password_change},
}

# Set `password` format for password change operation
USER_PWD_CHANGE_SCHEMA["properties"]["user"]["properties"]["password"][
    "format"
] = "password"
USER_PWD_CHANGE_SCHEMA["properties"]["user"]["properties"][
    "original_password"
]["format"] = "password"

USER_GROUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "The description of the group.",
        },
        "domain_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the domain of the group.",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the group.",
        },
        "name": {
            "type": "string",
            "description": "The name of the group.",
        },
        "membership_expires_at": {
            "type": "string",
            "format": "date-time",
            "description": "The date and time when the group membership expires. A null value indicates that the membership never expires.",
            "x-openstack": {"min-ver": "3.14"},
        },
    },
}

USER_GROUPS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "groups": {
            "type": "array",
            "description": "A list of group objects",
            "items": USER_GROUP_SCHEMA,
        }
    },
}

USER_PROJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "The description of the project.",
        },
        "domain_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the domain of the project.",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of the project.",
        },
        "parent_id": {
            "type": "string",
            "format": "uuid",
            "description": "The parent id of the project.",
        },
        "name": {
            "type": "string",
            "description": "The name of the project.",
        },
    },
}

USER_PROJECTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "projects": {
            "type": "array",
            "description": "A list of project objects",
            "items": USER_PROJECT_SCHEMA,
        }
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId

    if operationId == "users:get":
        for key, val in USER_LIST_PARAMETERS.items():
            openapi_spec.components.parameters.setdefault(
                key, ParameterSchema(**val)
            )
            ref = f"#/components/parameters/{key}"
            if ref not in [x.ref for x in operation_spec.parameters]:
                operation_spec.parameters.append(ParameterSchema(ref=ref))


def _get_schema_ref(
    openapi_spec,
    name,
    description=None,
    schema_def=None,
    action_name=None,
) -> tuple[str | None, str | None, bool]:
    mime_type: str = "application/json"
    ref: str
    # Users
    if name == "UserPatchRequest":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**USER_PATCH_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "UsersPostRequest":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**USER_CREATE_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "UsersGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**USERS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in ["UserGetResponse", "UserPostResponse", "UserPatchResponse"]:
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**USER_CONTAINER_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "UsersPasswordPostRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**USER_PWD_CHANGE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "UsersGroupsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**USER_GROUPS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "UsersProjectsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**USER_PROJECTS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
