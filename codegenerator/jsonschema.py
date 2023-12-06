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

import json
import logging

from codegenerator.base import BaseGenerator
from codegenerator.common.schema import TypeSchema


class JsonSchemaGenerator(BaseGenerator):
    """Generate jsonschema from the SDK resource"""

    def __init__(self):
        super().__init__()

    def _build_resource_schema(self, res):
        # resource = res.resource_class
        properties = {}
        for k, v in res.attrs.items():
            field = v["attr"]
            properties[field.name] = TypeSchema.from_sdk_field(
                field
            ).model_dump(
                exclude_none=True, exclude_defaults=True, by_alias=True
            )
            if "docs" in v:
                properties[field.name]["description"] = v["docs"]
            if k != field.name:
                properties[field.name]["x-openstack-sdk-name"] = k
            if k in [
                "created_at",
                "updated_at",
                "deleted_at",
                "id",
                "status",
                "trunk_details",
            ]:
                properties[field.name]["readOnly"] = True
            if k.startswith("min") or k.startswith("max") or "count" in k:
                properties[field.name]["type"] = "integer"
        if res.resource_class.resource_key:
            properties = {
                res.resource_class.resource_key: {
                    "type": "object",
                    "properties": properties,
                }
            }
        schema = TypeSchema(
            type="object", properties=properties, description=""
        )
        # if res.resource_class._store_unknown_attrs_as_properties:
        #    schema_attrs["additionalProperties"] = True
        # schema_attrs["properties"] = properties
        return schema

    def generate(
        self, res, target_dir, openapi_spec=None, operation_id=None, args=None
    ):
        """Generate Json Schema definition file for Resource"""
        logging.debug("Generating OpenAPI schema data")
        # We do not import generators since due to the use of Singletons in the
        # code importing glance, nova, cinder at the same time crashes
        # dramatically
        schema = self._build_resource_schema(res)
        print(
            json.dumps(
                json.loads(
                    schema.model_dump_json(
                        exclude_none=True, exclude_defaults=True, by_alias=True
                    )
                ),
                indent=4,
            )
        )
