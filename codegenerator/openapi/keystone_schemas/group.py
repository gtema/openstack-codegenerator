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

from codegenerator.common.schema import TypeSchema


GROUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "format": "uuid"},
        **identity_schema._group_properties,
    },
}

GROUPS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"groups": {"type": "array", "items": GROUP_SCHEMA}},
}


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
    if name == "GroupPatchRequest":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**identity_schema.user_update)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "GroupsPostRequest":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**identity_schema.user_create)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "GroupPatchResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**GROUP_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "GroupsGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**GROUPS_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"
    elif name == "GroupGetResponse":
        openapi_spec.components.schemas.setdefault(
            name, TypeSchema(**GROUP_SCHEMA)
        )
        ref = f"#/components/schemas/{name}"

    else:
        return (None, None, False)

    return (ref, mime_type, True)
