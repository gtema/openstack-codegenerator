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

from keystone.resource import schema as ks_schema

from codegenerator.common.schema import TypeSchema


DOMAIN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid", "readOnly": True},
        **ks_schema._domain_properties,
    },
    "additionalProperties": True,
}

DOMAINS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"domains": {"type": "array", "items": DOMAIN_SCHEMA}},
}


DOMAIN_CONFIG_GROUP_LDAP = {
    "type": "object",
    "description": "An ldap object. Required to set the LDAP group configuration options.",
    "properties": {
        "url": {
            "type": "string",
            "format": "uri",
            "description": "The LDAP URL.",
        },
        "user_tree_dn": {
            "type": "string",
            "description": "The base distinguished name (DN) of LDAP, from where all users can be reached. For example, ou=Users,dc=root,dc=org.",
        },
    },
    "additionalProperties": True,
}

DOMAIN_CONFIG_GROUP_IDENTITY = {
    "type": "object",
    "description": "An identity object.",
    "properties": {
        "driver": {
            "type": "string",
            "description": "The Identity backend driver.",
        },
    },
    "additionalProperties": True,
}

DOMAIN_CONFIGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "config": {
            "type": "object",
            "description": "A config object.",
            "properties": {
                "identity": DOMAIN_CONFIG_GROUP_IDENTITY,
                "ldap": DOMAIN_CONFIG_GROUP_LDAP,
            },
        }
    },
}

DOMAIN_CONFIG_SCHEMA: dict[str, Any] = {
    "oneOf": [
        DOMAIN_CONFIG_GROUP_IDENTITY,
        DOMAIN_CONFIG_GROUP_LDAP,
    ]
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    pass


def _get_schema_ref(
    openapi_spec,
    name,
    description=None,
    schema_def=None,
    action_name=None,
) -> tuple[str | None, str | None, bool]:
    mime_type: str = "application/json"
    ref: str
    # Domains
    if name in [
        "DomainsPostResponse",
        "DomainGetResponse",
        "DomainPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "Domain", TypeSchema(**DOMAIN_SCHEMA)
        )
        ref = "#/components/schemas/Domain"
    elif name == "DomainsPostRequest":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ks_schema.domain_create)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "DomainPatchRequest":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**ks_schema.domain_update)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "DomainsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**DOMAINS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"

    # Domain Config
    elif name in [
        "DomainsConfigDefaultGetResponse",
        "DomainsConfigGetResponse",
        "DomainsConfigPutRequest",
        "DomainsConfigPutResponse",
        "DomainsConfigPatchResponse",
        "DomainsConfigPatchRequest",
        "DomainsConfigPatchResponse",
        "DomainsConfigDefaultGetResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "DomainConfig",
            TypeSchema(**DOMAIN_CONFIGS_SCHEMA),
        )
        ref = "#/components/schemas/DomainConfig"
    elif name in [
        "DomainsConfigGroupGetResponse",
        "DomainsConfigGroupPatchRequest",
        "DomainsConfigGroupPatchResponse",
        "DomainsConfigGroupPatchResponse",
        "DomainsConfigGroupPatchResponse",
        "DomainsConfigDefaultGroupGetResponse",
        "DomainsConfigGroupOptionPatchResponse",
        "DomainsConfigGroupOptionGetResponse",
        "DomainsConfigGroupOptionPatchRequest",
    ]:
        openapi_spec.components.schemas.setdefault(
            "DomainConfigGroup",
            TypeSchema(**DOMAIN_CONFIG_SCHEMA),
        )
        ref = "#/components/schemas/DomainConfigGroup"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
