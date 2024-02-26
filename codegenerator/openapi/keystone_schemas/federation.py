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
    federation_mapping_schema.MAPPING_SCHEMA, proxies=False
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
