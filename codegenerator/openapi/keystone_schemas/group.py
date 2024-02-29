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
from codegenerator.openapi.keystone_schemas import user


GROUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid", "readOnly": True},
        **identity_schema._group_properties,
    },
}

GROUP_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"group": GROUP_SCHEMA},
}

GROUPS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"groups": {"type": "array", "items": GROUP_SCHEMA}},
}

GROUPS_LIST_PARAMETERS: dict[str, Any] = {
    "group_domain_id": {
        "in": "query",
        "name": "domain_id",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
}

GROUP_USERS_LIST_PARAMETERS: dict[str, Any] = {
    "group_user_password_expires_at": {
        "in": "query",
        "name": "password_expires_at",
        "description": "Filter results based on which user passwords have expired. The query should include an operator and a timestamp with a colon (:) separating the two, for example: `password_expires_at={operator}:{timestamp}`.\nValid operators are: `lt`, `lte`, `gt`, `gte`, `eq`, and `neq`.\nValid timestamps are of the form: YYYY-MM-DDTHH:mm:ssZ.",
        "schema": {"type": "string", "format": "date-time"},
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId

    if operationId == "groups:get":
        for key, val in GROUPS_LIST_PARAMETERS.items():
            openapi_spec.components.parameters.setdefault(
                key, ParameterSchema(**val)
            )
            ref = f"#/components/parameters/{key}"
            if ref not in [x.ref for x in operation_spec.parameters]:
                operation_spec.parameters.append(ParameterSchema(ref=ref))

    elif operationId == "groups/group_id/users:get":
        for key, val in GROUP_USERS_LIST_PARAMETERS.items():
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
    # Groups
    if name == "GroupsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**GROUPS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "GroupsPostRequest",
        "GroupsPostResponse",
        "GroupGetResponse",
        "GroupPatchRequest",
        "GroupPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "Group", TypeSchema(**GROUP_CONTAINER_SCHEMA)
        )
        ref = "#/components/schemas/Group"
    elif name == "GroupsUsersGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**user.USERS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "GroupsUserGetResponse",
        "GroupsUserPutRequest",
        "GroupsUserPutResponse",
    ]:
        return (None, None, True)
    else:
        return (None, None, False)

    return (ref, mime_type, True)
