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

from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field


class CommandTypeEnum(str, Enum):
    List = "list"
    Show = "show"
    Create = "create"
    Delete = "delete"
    Set = "set"
    Action = "action"
    Download = "download"
    Upload = "upload"
    Json = "json"


class SupportedTargets(str, Enum):
    OpenApiSchena = "openapi-schema"
    RustSdk = "rust-sdk"
    RustCli = "rust-cli"


class OperationTargetParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alternative_module_path: Optional[str] = None
    alternative_module_name: Optional[str] = None
    sdk_mod_path: Optional[str] = None
    cli_mod_path: Optional[str] = None
    command_type: Optional[CommandTypeEnum] = None
    command_name: Optional[str] = None
    service_type: Optional[str] = None
    api_version: Optional[str] = None
    request_key: Optional[str] = None
    response_key: Optional[str] = None
    response_list_item_key: Optional[str] = None


class OperationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str
    spec_file: str = Field(default=None)
    targets: dict[SupportedTargets, OperationTargetParams]


class ResourceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    spec_file: str
    api_version: Optional[str] = None
    operations: dict[str, OperationModel]
    extensions: dict[str, dict] = Field(default={})


class Metadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resources: dict[str, ResourceModel]


# Stripped and normalized types derived from JsonSchema used by generators
class BaseType(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    description: str | None = None
    is_nullable: bool = False
    schema_type: str | list[str] | None = Field(alias="type", default=None)

    @classmethod
    def parse(cls, schema):
        self = cls(**schema)
        return self


class StringType(BaseType):
    format: str | None = None
    minLength: int | None = None


class NumberType(BaseType):
    format: str | None = None


class IntegerType(BaseType):
    format: str | None = None


class BooleanType(BaseType):
    pass


class NullType(BaseType):
    pass


class ObjectType(BaseType):
    properties: dict[str, BaseType] = {}

    @classmethod
    def parse(cls, schema):
        self = cls(**schema)
        properties = schema.get("properties", {})
        for k, v in properties.items():
            self.properties[k] = get_type_from_schema(v, name=k)
        return self


class ArrayType(BaseType):
    items: Any = []

    @classmethod
    def __init__(cls, schema):
        self = cls(**schema)
        self.items = get_type_from_schema(schema.get("items"))
        return self


class UnionType(BaseType):
    kinds: dict[str, BaseType] = {}

    @classmethod
    def parse(cls, schema=None):
        self = cls(**schema)
        cnt = 0
        if schema:
            for candidate in schema.get("oneOf"):
                cnt += 1
                os_ext = candidate.get("x-openstack", {})
                kind_name = os_ext.get("kind-name", f"F{cnt}")
                self.kinds[kind_name] = get_type_from_schema(candidate)
        return self


def get_type_from_schema(schema, name: str = None):
    xtype: str | list[str] | None = schema.get("type")
    oneOf: list | None = schema.get("oneOf")
    res: BaseType | None = None
    is_nullable: bool | None = None
    if xtype and isinstance(xtype, list):
        # Type is a combination of types
        if len(xtype) > 1 and "null" in xtype:
            # Convert type list into nullable type
            xtype.remove("null")
            is_nullable = True
        if len(xtype) > 1:
            if set(["integer", "string"]) == set(xtype):
                # Server support int or string. We are interested in int only
                xtype = "integer"
            elif set(["number", "string"]) == set(xtype):
                # Server support number or string. We are interested in bool only
                xtype = "number"
            elif set(["boolean", "string"]) == set(xtype):
                # Server support bool or string. We are interested in bool only
                xtype = "boolean"
            else:
                # Convert type combination to the oneOf
                res = UnionType()
                cnt = 0
                for typ in xtype:
                    cnt += 1
                    kind: BaseType = None
                    if typ == "string":
                        kind = StringType.parse(schema)
                    elif typ == "integer":
                        kind = IntegerType.parse(schema)
                    elif typ == "number":
                        kind = IntegerType.parse(schema)
                    elif typ == "array":
                        kind = ArrayType.parse(schema)
                    elif typ == "object":
                        kind = ObjectType.parse(schema)

                    else:
                        raise RuntimeError(
                            "Type combination with %s is not supported" % typ
                        )
                    res.kinds[f"F{cnt}"] = kind
        else:
            xtype = xtype[0]

    if xtype and isinstance(xtype, str):
        # Type is set and it a strict type
        if xtype == "string":
            res = StringType.parse(schema)
        elif xtype == "integer":
            res = IntegerType.parse(schema)
        elif xtype == "number":
            res = NumberType.parse(schema)
        elif xtype == "boolean":
            res = BooleanType.parse(schema)
        elif xtype == "array":
            res = ArrayType.parse(schema)
        elif xtype == "object":
            res = ObjectType.parse(schema)
        elif xtype == "null":
            res = NullType.parse(schema)

    elif schema == {}:
        # nova legacy_block_device_mapping.no_device is "{}"
        res = NullType()
    elif oneOf:
        res = UnionType.parse(schema)
    if not res:
        raise RuntimeError("JsonSchema %s is not supported yet" % schema)
    description = schema.get("description")
    if name:
        res.name = name
    if description:
        res.description = description
    if is_nullable is not None:
        res.is_nullable = is_nullable

    return res
