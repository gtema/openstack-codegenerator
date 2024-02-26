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
        },
        "name": {
            "type": "string",
            "description": "The service name.",
        },
        "type": {
            "type": "string",
            "description": "The service type, which describes the API implemented by the service.",
        },
    },
}

SERVICE_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"service": SERVICE_SCHEMA},
}

SERVICE_CREATE_SCHEMA: dict[str, Any] = copy.deepcopy(SERVICE_CONTAINER_SCHEMA)
SERVICE_CREATE_SCHEMA["properties"]["service"]["properties"].pop("id")
SERVICE_CREATE_SCHEMA["properties"]["service"]["required"] = ["type"]
SERVICE_UPDATE_SCHEMA: dict[str, Any] = copy.deepcopy(SERVICE_CONTAINER_SCHEMA)
SERVICE_UPDATE_SCHEMA["properties"]["service"]["properties"].pop("id")


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
