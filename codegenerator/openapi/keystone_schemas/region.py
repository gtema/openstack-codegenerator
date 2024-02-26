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
