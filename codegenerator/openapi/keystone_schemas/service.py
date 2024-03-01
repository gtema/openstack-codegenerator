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

from codegenerator.common.schema import TypeSchema
from codegenerator.common.schema import ParameterSchema


SERVICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "The service description.",
        },
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
        "name": {
            "type": "string",
            "description": "The service name.",
        },
        "type": {
            "type": "string",
            "description": "The service type, which describes the API implemented by the ",
        },
    },
}

SERVICE_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"service": SERVICE_SCHEMA},
}

SERVICES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"services": {"type": "array", "items": SERVICE_SCHEMA}},
}

SERVICES_LIST_PARAMETERS = {
    "service_type": {
        "in": "query",
        "name": "service",
        "description": "Filters the response by a domain ID.",
        "schema": {"type": "string"},
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId
    if operationId == "services:get":
        for (
            key,
            val,
        ) in SERVICES_LIST_PARAMETERS.items():
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
    # ### Services
    if name == "ServicesGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**SERVICES_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "ServicesPostRequest",
        "ServicesPostResponse",
        "ServiceGetResponse",
        "ServicePatchRequest",
        "ServicePatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "Service",
            TypeSchema(**SERVICE_CONTAINER_SCHEMA),
        )
        ref = "#/components/schemas/Service"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
