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
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

# from openapi_core import Spec


class TypeSchema(BaseModel):
    # TODO(gtema): enums are re-shuffled on every serialization
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: Optional[str | List[str]] = None
    format: Optional[str] = None
    description: Optional[str] = None
    summary: str | None = None
    default: Optional[Any] = None
    items: Optional[Dict[str, Any]] = None
    # circular reference cause issues on deserializing
    properties: Optional[Dict[str, Any]] = None
    nullable: Optional[bool] = None
    additionalProperties: Optional[bool | Any] = None

    ref: Optional[str] = Field(alias="$ref", default=None)
    oneOf: Optional[List[Any]] = Field(default=None)
    anyOf: Optional[List[Any]] = Field(default=None)
    openstack: Optional[Dict[str, Any]] = Field(
        alias="x-openstack", default=None
    )
    required: Optional[List[str]] = None
    pattern: Optional[str] = None
    maxLength: Optional[int] = None

    @classmethod
    def openapi_type_from_sdk(cls, type_name, fallback_type):
        if type_name in ["string", "str"]:
            return {"type": "string"}
        elif type_name == "int":
            return {"type": "integer"}
        elif type_name == "bool":
            return {"type": "boolean"}
        elif type_name == "dict":
            return {"type": "object"}
        elif type_name == "list":
            return {"type": "array"}
        else:
            # This is a fallback. Maybe we should define those objects
            return {"type": fallback_type}

    @classmethod
    def from_sdk_field(cls, field, fallback_type="object"):
        property_schema_attrs = {}
        if field.type:
            field_type = getattr(field.type, "__name__", "string")
        else:
            field_type = "string"

        property_schema_attrs.update(
            cls.openapi_type_from_sdk(field_type, fallback_type)
        )
        if field_type == "list":
            item_type = getattr(field, "list_type")
            item_type_str = getattr(item_type, "__name__", "string")
            property_schema_attrs["items"] = cls.openapi_type_from_sdk(
                item_type_str, fallback_type
            )

        return cls(**property_schema_attrs)


class ParameterSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    location: str = Field(alias="in", default=None)
    name: str | None = None
    description: str | None = None
    type_schema: TypeSchema = Field(alias="schema", default=None)
    required: bool = False
    deprecated: bool = False
    style: str | None = None
    explode: bool | None = None
    ref: str = Field(alias="$ref", default=None)
    openstack: Dict[str, Any] = Field(alias="x-openstack", default=None)

    def get_sdk_name(self):
        return self.sdk_name or self.name


class OperationSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    parameters: List[ParameterSchema] = []
    description: str | None = None
    operationId: str | None = None
    requestBody: dict = {}
    responses: Dict[str, dict] = {}
    tags: List[str] = list()
    deprecated: bool | None = None
    openstack: dict = Field(alias="x-openstack", default={})
    security: List | None = None


class HeaderSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    description: Optional[str] = None
    openstack: Optional[Dict[str, Any]] = Field(
        alias="x-openstack", default=None
    )
    schema: Optional[TypeSchema] = Field(default=None)


class PathSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    parameters: List[ParameterSchema] = []
    get: OperationSchema = OperationSchema()
    post: OperationSchema = OperationSchema()
    delete: OperationSchema = OperationSchema()
    put: OperationSchema = OperationSchema()
    patch: OperationSchema = OperationSchema()
    head: OperationSchema = OperationSchema()


class ComponentsSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    schemas: Dict[str, TypeSchema] = {}
    parameters: Dict[str, ParameterSchema] = {}
    headers: Dict[str, HeaderSchema] = {}


class SpecSchema(BaseModel):
    class Config:
        pupulate_by_name = True
        extra = "allow"

    openapi: str
    info: dict
    paths: Dict[str, PathSchema] = {}
    components: ComponentsSchema = ComponentsSchema()
    tags: List[Dict] = []
    security: List[Dict] = []
