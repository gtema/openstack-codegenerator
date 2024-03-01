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

REGION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {
            "type": "string",
            "description": "The region description.",
        },
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "The ID for the region.",
            "readOnly": True,
        },
        "parent_id": {
            "type": "string",
            "format": "uuid",
            "description": "To make this region a child of another region, set this parameter to the ID of the parent region.",
        },
    },
}

REGION_CONTAINER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"region": REGION_SCHEMA},
}

REGIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"regions": {"type": "array", "items": REGION_SCHEMA}},
}

REGIONS_LIST_PARAMETERS = {
    "region_parent_region_id": {
        "in": "query",
        "name": "parent_region_id",
        "description": "Filters the response by a parent region, by ID.",
        "schema": {"type": "string", "format": "uuid"},
    },
}


def _post_process_operation_hook(
    openapi_spec, operation_spec, path: str | None = None
):
    """Hook to allow service specific generator to modify details"""
    operationId = operation_spec.operationId
    if operationId == "regions:get":
        for (
            key,
            val,
        ) in REGIONS_LIST_PARAMETERS.items():
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
    # ### Regions
    if name == "RegionsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name,
            TypeSchema(**REGIONS_SCHEMA),
        )
        ref = f"#/components/schemas/{name}"
    elif name in [
        "RegionGetResponse",
        "RegionsPostRequest",
        "RegionsPostResponse",
        "RegionPatchRequest",
        "RegionPatchResponse",
    ]:
        openapi_spec.components.schemas.setdefault(
            "Region",
            TypeSchema(**REGION_CONTAINER_SCHEMA),
        )
        ref = "#/components/schemas/Region"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
