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
from codegenerator.common.schema import ParameterSchema

ENDPOINT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean",
            "description": "Defines whether the service and its endpoints appear in the service catalog.",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the service to which the endpoint belongs.",
            "readOnly": True,
        },
        "interface": {
            "type": "string",
            "enum": ["internal", "admin", "public"],
            "description": "The interface type, which describes the visibility of the  Value is: - public. Visible by end users on a publicly available network interface. - internal. Visible by end users on an unmetered internal network interface. - admin. Visible by administrative users on a secure network interface.",
        },
        "region": {
            "type": "string",
            "description": "The geographic location of the service endpoint.",
            "x-openstack": {"max-ver": "3.2"},
        },
        "region_id": {
            "type": "string",
            "format": "uuid",
            "description": "The geographic location of the service ",
            "x-openstack": {"min-ver": "3.2"},
        },
        "service_id": {
            "type": "string",
            "format": "uuid",
            "description": "The UUID of the service to which the endpoint belongs.",
        },
        "url": {
            "type": "string",
            "format": "uri",
            "description": "The endpoint URL.",
        },
    },
}

ENDPOINT_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"endpoint": ENDPOINT_SCHEMA},
}

ENDPOINTS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"endpoints": {"type": "array", "items": ENDPOINT_SCHEMA}},
}

ENDPOINTS_LIST_PARAMETERS = {
    "endpoint_service_id": {
        "in": "query",
        "name": "service_id",
        "description": "Filters the response by a service ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "endpoint_region_id": {
        "in": "query",
        "name": "region",
        "description": "Filters the response by a region ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
    "endpoint_interface": {
        "in": "query",
        "name": "interface",
        "description": "Filters the response by an interface.",
        "schema": {"type": "string", "enum": ["public", "internal", "admin"]},
    },
}

ENDPOINT_CREATE_SCHEMA: dict[str, Any] = copy.deepcopy(
    ENDPOINT_CONTAINER_SCHEMA
)
ENDPOINT_CREATE_SCHEMA["properties"]["endpoint"]["properties"].pop("id")
ENDPOINT_CREATE_SCHEMA["properties"]["endpoint"]["required"] = [
    "interface",
    "service_id",
    "url",
]


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId
    if operationId == "endpoints:get":
        for (
            key,
            val,
        ) in ENDPOINTS_LIST_PARAMETERS.items():
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
    # ### Endpoints
    if name == "EndpointsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**ENDPOINTS_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "EndpointGetResponse",
        "EndpointsPostRequest",
        "EndpointsPostResponse",
        "EndpointPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "Endpoint",
            TypeSchema(**ENDPOINT_CONTAINER_SCHEMA),
        )
        ref = "#/components/schemas/Endpoint"
    elif name == "EndpointsPostRequest":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**ENDPOINT_CREATE_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
