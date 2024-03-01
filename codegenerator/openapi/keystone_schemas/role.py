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

from keystone.assignment import schema as assignment_schema

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import TypeSchema
from codegenerator.openapi.keystone_schemas import auth

ROLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A role object.",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The role ID.",
            "readOnly": True,
        },
        "links": {
            "type": "object",
            "additionalProperties": {
                "type": ["string", "null"],
                "format": "uri",
            },
            "readOnly": True,
        },
        **assignment_schema._role_properties,
    },
}

ROLE_INFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The role ID.",
        },
        "name": {
            "type": "string",
            "description": "The role name.",
        },
        "description": {
            "type": "string",
            "description": "The role description.",
        },
        "links": {
            "type": "object",
            "properties": {
                "self": {
                    "type": "string",
                    "format": "uri",
                    "description": "The link to the resource in question.",
                }
            },
        },
    },
}

ROLE_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"role": ROLE_SCHEMA},
}

ROLES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "roles": {"type": "array", "items": ROLE_SCHEMA},
        "links": {
            "type": "object",
            "additionalProperties": {
                "type": ["string", "null"],
                "format": "uri",
            },
        },
    },
}

# List of role info
ROLES_INFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "List of roles assigned to the resource",
    "properties": {
        "roles": {"type": "array", "items": ROLE_INFO_SCHEMA},
        "links": {
            "type": "object",
            "additionalProperties": {
                "type": ["string", "null"],
                "format": "uri",
            },
        },
    },
}

# Role list specific query parameters
ROLE_LIST_PARAMETERS: dict[str, Any] = {
    "role_domain_id": {
        "in": "query",
        "name": "domain_id",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
}


ROLE_INFERENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role_inference": {
            "type": "object",
            "properties": {
                "prior_role": ROLE_INFO_SCHEMA,
                "implies": ROLE_INFO_SCHEMA,
            },
        }
    },
}

ROLES_INFERENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role_inference": {
            "type": "object",
            "properties": {
                "prior_role": ROLE_INFO_SCHEMA,
                "implies": {
                    "type": "array",
                    "items": ROLE_INFO_SCHEMA,
                },
            },
        }
    },
}

ROLES_INFERENCES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role_inferences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prior_role": ROLE_INFO_SCHEMA,
                    "implies": {
                        "type": "array",
                        "items": ROLE_INFO_SCHEMA,
                    },
                },
            },
        }
    },
}

USER_INFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A user object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "A user UUID",
        },
        "name": {"type": "string", "description": "A user name"},
        "domain": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "description": "A user domain UUID",
                },
                "name": {
                    "type": "string",
                    "description": "A user domain name",
                },
            },
        },
    },
}

GROUP_INFO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid", "description": "A user ID"},
        "name": {"type": "string", "description": "A user name"},
    },
}

ROLE_ASSIGNMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role": ROLE_INFO_SCHEMA,
        "scope": auth.SCOPE_SCHEMA,
        "user": USER_INFO_SCHEMA,
        "group": GROUP_INFO_SCHEMA,
        "links": {
            "type": "object",
            "properties": {
                "assignment": {
                    "type": "string",
                    "format": "uri",
                    "description": "a link to the assignment that gave rise to this entity",
                },
                "membership": {
                    "type": "string",
                    "format": "uri",
                },
            },
        },
    },
}

ROLE_ASSIGNMENTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "role_assignments": {"type": "array", "items": ROLE_ASSIGNMENT_SCHEMA}
    },
}

#: Role assignment query parameters common for LIST and HEAD
ROLE_ASSIGNMENTS_QUERY_PARAMETERS: dict[str, Any] = {
    "role_assignment_group_id": {
        "in": "query",
        "name": "group.id",
        "description": "Filters the response by a group ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "role_assignment_role_id": {
        "in": "query",
        "name": "role.id",
        "description": "Filters the response by a role ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "role_assignment_user_id": {
        "in": "query",
        "name": "user.id",
        "description": "Filters the response by a user ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "role_assignment_scope_domain_id": {
        "in": "query",
        "name": "scope.domain.id",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "role_assignment_scope_project_id": {
        "in": "query",
        "name": "scope.project.id",
        "description": "Filters the response by a project ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "role_assignment_inherit": {
        "in": "query",
        "name": "scope.OS-INHERIT:inherited_to",
        "description": "Filters based on role assignments that are inherited. The only value of inherited_to that is currently supported is projects.",
        "schema": {"type": "string", "format": "uuid"},
    },
}

# Role assignments list specific query parameters
ROLE_ASSIGNMENT_LIST_PARAMETERS: dict[str, Any] = {
    "role_assignment_effective": {
        "in": "query",
        "name": "effective",
        "description": "Returns the effective assignments, including any assignments gained by virtue of group membership.",
        "schema": {"type": "null"},
        "allowEmptyValue": True,
        "x-openstack": {"is-flag": True},
    },
    "role_assignment_include_names": {
        "in": "query",
        "name": "include_names",
        "description": "If set, then the names of any entities returned will be include as well as their IDs. Any value other than 0 (including no value) will be interpreted as true.",
        "schema": {"type": "null"},
        "allowEmptyValue": True,
        "x-openstack": {"min-ver": "3.6", "is-flag": True},
    },
    "role_assignment_include_subtree": {
        "in": "query",
        "name": "include_subtree",
        "description": "If set, then relevant assignments in the project hierarchy below the project specified in the scope.project_id query parameter are also included in the response. Any value other than 0 (including no value) for include_subtree will be interpreted as true.",
        "schema": {"type": "null"},
        "allowEmptyValue": True,
        "x-openstack": {"min-ver": "3.6", "is-flag": "True"},
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId

    if operationId == "roles:get":
        for (
            key,
            val,
        ) in ROLE_LIST_PARAMETERS.items():
            openapi_spec.components.parameters.setdefault(
                key, ParameterSchema(**val)
            )
            ref = f"#/components/parameters/{key}"

            if ref not in [x.ref for x in operation_spec.parameters]:
                operation_spec.parameters.append(ParameterSchema(ref=ref))
    elif operationId == "role_assignments:get":
        for map in [
            ROLE_ASSIGNMENTS_QUERY_PARAMETERS,
            ROLE_ASSIGNMENT_LIST_PARAMETERS,
        ]:
            for (
                key,
                val,
            ) in map.items():
                openapi_spec.components.parameters.setdefault(
                    key, ParameterSchema(**val)
                )
                ref = f"#/components/parameters/{key}"

                if ref not in [x.ref for x in operation_spec.parameters]:
                    operation_spec.parameters.append(ParameterSchema(ref=ref))
    elif operationId == "role_assignments:head":
        for (
            key,
            val,
        ) in ROLE_ASSIGNMENTS_QUERY_PARAMETERS.items():
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
    # Roles
    if name == "RolesGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ROLES_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "RolesPostRequest",
        "RolesPostResponse",
        "RoleGetResponse",
        "RolePatchRequest",
        "RolePatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "Role", TypeSchema(**ROLE_CONTAINER_SCHEMA)
        )
        ref = "#/components/schemas/Role"

    # Role Implies
    elif name == "RolesImpliesGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**ROLES_INFERENCE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "RolesImplyGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ROLE_INFERENCE_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "RolesImplyPutResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ROLE_INFERENCE_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"

    elif name == "Role_AssignmentsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ROLE_ASSIGNMENTS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    # Role Inferences
    elif name == "Role_InferencesGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ROLES_INFERENCES_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"

    # Project/Domain Roles
    elif name in [
        "ProjectsUsersRolesGetResponse",
        "DomainsGroupsRolesGetResponse",
        "ProjectsGroupsRolesGetResponse",
        "DomainsUsersRolesGetResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "RolesInfos", TypeSchema(**ROLES_INFO_SCHEMA)
        )
        ref = "#/components/schemas/RolesInfos"
    elif name in [
        "DomainsUsersRoleGetResponse",
        "DomainsUsersRolePutRequest",
        "DomainsUsersRolePutResponse",
        "DomainsGroupsRoleGetResponse",
        "DomainsGroupsRolePutRequest",
        "DomainsGroupsRolePutResponse",
        "ProjectsUsersRoleGetResponse",
        "ProjectsUsersRolePutRequest",
        "ProjectsUsersRolePutResponse",
        "ProjectsGroupsRoleGetResponse",
        "ProjectsGroupsRolePutRequest",
        "ProjectsGroupsRolePutResponse",
    ]:
        return (None, None, True)

    else:
        return (None, None, False)

    return (ref, mime_type, True)
