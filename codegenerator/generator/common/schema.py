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

    # sdk_name: str = Field(
    #    alias="x-openstack-sdk-name", default=None
    # )
    # min_microversion: str = Field(
    #    alias="x-openstack-min-microversion", default=None
    # )
    # max_microversion: str = Field(
    #    alias="x-openstack-max-microversion", default=None
    # )
    # openstack_default: str = Field(
    #    alias="x-openstack-default", default=None
    # )

    def rust_sdk_type(self):
        if self.type in ["str", "string"]:
            return "Cow<'a, str>"
        elif self.type == "number":
            if self.format:
                if self.format == "float":
                    return "f32"
                elif self.format == "double":
                    return "f64"
            return "i32"
        elif self.type == "integer":
            if self.format:
                if self.format == "int32":
                    return "i32"
                elif self.format == "int64":
                    return "i64"
            return "i32"
        raise ValueError("Type %s is not supported for Rust" % self.type)

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
    name: str = None
    description: str = None
    type_schema: TypeSchema = Field(alias="schema", default=None)
    required: bool = False
    # min_version: str = Field(alias="x-min-version", default=None)
    # max_version: str = Field(alias="x-max-version", default=None)
    deprecated: bool = False
    style: str = None
    explode: bool = None
    ref: str = Field(alias="$ref", default=None)
    openstack: Dict[str, Any] = Field(alias="x-openstack", default=None)

    def rust_sdk_type(self):
        if self.type_schema.type == "array":
            element_type = TypeSchema(**self.type_schema.items).rust_sdk_type()
            if (
                self.location == "query"
                and self.style == "form"
                and not self.explode
            ):
                param_type = f"CommaSeparatedList<{element_type}>"
        else:
            param_type = self.type_schema.rust_sdk_type()
        if not self.required:
            return f"Option<{param_type}>"
        else:
            return param_type

    def get_sdk_name(self):
        return self.sdk_name or self.name


class OperationSchema(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    parameters: List[ParameterSchema] = []
    description: str = None
    operationId: str = None
    requestBody: dict = {}
    responses: Dict[str, dict] = {}
    tags: List[str] = list()
    deprecated: bool = None
    openstack: dict = Field(alias="x-openstack", default={})
    security: List = None


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
    # headers = Dict[str, TypeSchema] = Field(default=None)


class SpecSchema(BaseModel):
    class Config:
        # You can override these fields, which affect JSON and YAML:
        # json_dumps = my_custom_dumper
        # json_loads = lambda x: SpecSchema()
        # As well as other Pydantic configuration:
        # allow_mutation = False
        pupulate_by_name = True
        extra = "allow"

    # model_config = ConfigDict(extra="allow", populate_by_name=True)

    openapi: str
    info: dict
    paths: Dict[str, PathSchema] = {}
    components: ComponentsSchema = {}
    tags: List[Dict] = []
    security: List[Dict] = []
