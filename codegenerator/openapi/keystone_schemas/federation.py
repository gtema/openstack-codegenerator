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

from jsonref import replace_refs

from keystone.federation import schema as federation_schema
from keystone.federation import utils as federation_mapping_schema

from codegenerator.common.schema import ParameterSchema
from codegenerator.common.schema import TypeSchema
from codegenerator.openapi.keystone_schemas import auth


IDENTITY_PROVIDER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "The Identity Provider unique ID",
        },
        "description": {
            "type": "string",
            "description": "The Identity Provider description",
        },
        "domain_id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID of a domain that is associated with the Identity Provider.",
        },
        "authorization_ttl": {
            "type": "integer",
            "description": "The length of validity in minutes for group memberships carried over through mapping and persisted in the database.",
        },
        "enabled": {
            "type": "boolean",
            "description": "Whether the Identity Provider is enabled or not",
        },
        "remote_ids": {
            "type": "array",
            "description": "List of the unique Identity Provider’s remote IDs",
            "items": {"type": "string"},
        },
    },
}

IDENTITY_PROVIDER_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"identity_provider": IDENTITY_PROVIDER_SCHEMA},
}

IDENTITY_PROVIDER_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "identity_provider": federation_schema.identity_provider_create
    },
}

IDENTITY_PROVIDER_UPDATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "identity_provider": federation_schema.identity_provider_update
    },
}

IDENTITY_PROVIDERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "identity_providers": {
            "type": "array",
            "items": IDENTITY_PROVIDER_SCHEMA,
        }
    },
}

IDENTITY_PROVIDERS_LIST_PARAMETERS: dict[str, Any] = {
    "idp_id": {
        "in": "query",
        "name": "id",
        "description": "Filter for Identity Providers’ ID attribute",
        "schema": {"type": "string"},
    },
    "idp_enabled": {
        "in": "query",
        "name": "enabled",
        "description": "Filter for Identity Providers’ enabled attribute",
        "schema": {"type": "boolean"},
    },
}

IDENTITY_PROVIDER_PROTOCOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The federation protocol ID",
        },
        "mapping_id": {"type": "string"},
        "remote_id_attribute": {"type": "string", "maxLength": 64},
    },
}

IDENTITY_PROVIDER_PROTOCOL_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"protocol": IDENTITY_PROVIDER_PROTOCOL_SCHEMA},
}

IDENTITY_PROVIDER_PROTOCOLS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "protocols": {
            "type": "array",
            "items": IDENTITY_PROVIDER_PROTOCOL_SCHEMA,
        }
    },
}

IDENTITY_PROVIDER_PROTOCOL_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"protocol": federation_schema.protocol_create},
}

IDENTITY_PROVIDER_PROTOCOL_UPDATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"protocol": federation_schema.protocol_update},
}

MAPPING_PROPERTIES = replace_refs(
    (
        federation_mapping_schema.IDP_ATTRIBUTE_MAPPING_SCHEMA_1_0
        if hasattr(federation_mapping_schema, "IDP_ATTRIBUTE_MAPPING_SCHEMA")
        else federation_mapping_schema.MAPPING_SCHEMA
    ),
    proxies=False,
)
MAPPING_PROPERTIES.pop("definitions", None)
MAPPING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "The Federation Mapping unique ID",
        },
        **MAPPING_PROPERTIES["properties"],
    },
}

MAPPING_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"mapping": MAPPING_SCHEMA},
}

MAPPINGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"mappings": {"type": "array", "items": MAPPING_SCHEMA}},
}

MAPPING_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"mapping": MAPPING_PROPERTIES},
}

FEDERATION_SERVICE_PROVIDER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "auth_url": {
            "type": "string",
            "description": "The URL to authenticate against",
        },
        "description": {
            "type": ["string", "null"],
            "description": "The description of the Service Provider",
        },
        "id": {
            "type": "string",
            "description": "The Service Provider unique ID",
        },
        "enabled": {
            "type": "boolean",
            "description": "Whether the Service Provider is enabled or not",
        },
        "relay_state_prefix": {
            "type": ["string", "null"],
            "description": "The prefix of the RelayState SAML attribute",
        },
        "sp_url": {
            "type": "string",
            "description": "The Service Provider’s URL",
        },
    },
    "required": ["auth_url", "sp_url"],
}

FEDERATION_SERVICE_PROVIDER_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"service_provider": FEDERATION_SERVICE_PROVIDER_SCHEMA},
}

FEDERATION_SERVICE_PROVIDERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "service_providers": {
            "type": "array",
            "items": FEDERATION_SERVICE_PROVIDER_SCHEMA,
        }
    },
}

FEDERATION_SERVICE_PROVIDER_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "service_provider": federation_schema.service_provider_create
    },
}

FEDERATION_SERVICE_PROVIDER_UPDATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "service_provider": federation_schema.service_provider_update
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId
    if operationId == "OS-FEDERATION/identity_providers:get":
        for (
            key,
            val,
        ) in IDENTITY_PROVIDERS_LIST_PARAMETERS.items():
            openapi_spec.components.parameters.setdefault(
                key, ParameterSchema(**val)
            )
            ref = f"#/components/parameters/{key}"
            if ref not in [x.ref for x in operation_spec.parameters]:
                operation_spec.parameters.append(ParameterSchema(ref=ref))
    elif operationId in [
        "OS-FEDERATION/projects:get",
        "OS-FEDERATION/projects:head",
        "OS-FEDERATION/domains:get",
        "OS-FEDERATION/domains:head",
        "endpoints/endpoint_id/OS-ENDPOINT-POLICY/policy:get",
    ]:
        operation_spec.deprecated = True


def _get_schema_ref(
    openapi_spec,
    name,
    description=None,
    schema_def=None,
    action_name=None,
) -> tuple[str | None, str | None, bool]:
    mime_type: str = "application/json"
    ref: str | None
    if name == "Os_FederationProjectsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**auth.AUTH_PROJECTS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "Os_FederationDomainsGetResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**auth.AUTH_DOMAINS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "AuthOs_FederationSaml2PostRequest",
        "AuthOs_FederationSaml2EcpPostRequest",
    ]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**auth.AUTH_TOKEN_ISSUE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "AuthOs_FederationSaml2PostResponse",
        "AuthOs_FederationSaml2EcpPostResponse",
    ]:
        mime_type = "text/xml"
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(
                type="string",
                format="xml",
                descripion="SAML assertion in XML format",
            ),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "AuthOs_FederationWebssoGetResponse",
        "AuthOs_FederationWebssoPostResponse",
        "AuthOs_FederationIdentity_ProvidersProtocolsWebssoGetResponse",
        "AuthOs_FederationIdentity_ProvidersProtocolsWebssoPostResponse",
        "Os_FederationIdentity_ProvidersProtocolsAuthGetResponse",
        "Os_FederationIdentity_ProvidersProtocolsAuthPostResponse",
    ]:
        # Federation based auth returns unscoped token even it is not
        # described explicitly in apiref
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**auth.AUTH_TOKEN_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "AuthOs_FederationWebssoPostRequest",
        "AuthOs_FederationIdentity_ProvidersProtocolsWebssoPostRequest",
    ]:
        ref = None
    # ### Identity provider
    elif name == "Os_FederationIdentity_ProvidersGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDERS_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "Os_FederationIdentity_ProviderGetResponse",
        "Os_FederationIdentity_ProviderPutResponse",
        "Os_FederationIdentity_ProviderPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_CONTAINER_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "Os_FederationIdentity_ProviderPutRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_CREATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "Os_FederationIdentity_ProviderPatchRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_UPDATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    # ### Identity provider protocols
    elif name == "Os_FederationIdentity_ProvidersProtocolsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_PROTOCOLS_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "Os_FederationIdentity_ProvidersProtocolGetResponse",
        "Os_FederationIdentity_ProvidersProtocolPutResponse",
        "Os_FederationIdentity_ProvidersProtocolPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_PROTOCOL_CONTAINER_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "Os_FederationIdentity_ProvidersProtocolPutRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_PROTOCOL_CREATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "Os_FederationIdentity_ProvidersProtocolPatchRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**IDENTITY_PROVIDER_PROTOCOL_UPDATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    # ### Identity provider mapping
    elif name == "Os_FederationMappingsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**MAPPINGS_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "Os_FederationMappingGetResponse",
        "Os_FederationMappingPutResponse",
        "Os_FederationMappingPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**MAPPING_CONTAINER_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "Os_FederationMappingPutRequest",
        "Os_FederationMappingPatchRequest",
    ]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**MAPPING_CREATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    # ### Identity provider service provider
    elif name == "Os_FederationService_ProvidersGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**FEDERATION_SERVICE_PROVIDERS_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "Os_FederationService_ProviderGetResponse",
        "Os_FederationService_ProviderPutResponse",
        "Os_FederationService_ProviderPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**FEDERATION_SERVICE_PROVIDER_CONTAINER_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "Os_FederationService_ProviderPutRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**FEDERATION_SERVICE_PROVIDER_CREATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name == "Os_FederationService_ProviderPatchRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**FEDERATION_SERVICE_PROVIDER_UPDATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    # SAML2 Metadata
    elif name == "Os_FederationSaml2MetadataGetResponse":
        mime_type = "text/xml"
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(
                type="string",
                format="xml",
                descripion="Identity Provider metadata information in XML format",
            ),
        )
        ref = f"#/components/schemas/{name}"
    else:
        return (None, None, False)

    return (ref, mime_type, True)
