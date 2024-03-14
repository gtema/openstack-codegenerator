# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
import copy
import hashlib
import json
import logging
from typing import Any
from typing import Type
import typing as ty

from pydantic import BaseModel

from codegenerator import common


def dicthash_(data: dict[str, Any]) -> str:
    """Calculate hash of the dictionary"""
    dh = hashlib.md5()
    encoded = json.dumps(data, sort_keys=True).encode()
    dh.update(encoded)
    return dh.hexdigest()


class Reference(BaseModel):
    """Reference of the complex type to the occurence instance"""

    #: Name of the object that uses the type under reference
    name: str
    type: Type | None = None
    hash_: str | None = None

    def __hash__(self):
        return hash((self.name, self.type, self.hash_))


class PrimitiveType(BaseModel):
    """Primitive Data Type stricture"""

    pass


class PrimitiveString(PrimitiveType):
    pass


class ConstraintString(PrimitiveType):
    format: str | None = None
    minLength: int | None = None
    maxLength: int | None = None
    pattern: str | None = None
    enum: list[Any] | None = None


class PrimitiveNumber(PrimitiveType):
    pass


class ConstraintNumber(PrimitiveNumber):
    format: str | None = None
    minimum: int | None = None
    maximum: int | float | None = None
    exclusiveMaximum: bool | None = None
    multipleOf: int | float | None = None


class ConstraintInteger(ConstraintNumber):
    pass


class PrimitiveBoolean(PrimitiveType):
    pass


class PrimitiveNull(PrimitiveType):
    pass


class PrimitiveAny(PrimitiveType):
    pass


class ADT(BaseModel):
    """Abstract Data Type / Composite - typically sort of
    collection of Primitives"""

    reference: Reference | None = None
    description: str | None = None


class AbstractList(ADT):
    """Abstract list"""

    item_type: PrimitiveType | ADT | Reference


class AbstractCollection(ADT):
    """AllOf/OneOf/etc"""

    pass


class AbstractContainer(ADT):
    """Struct/Object"""

    pass


class OneOfType(ADT):
    """OneOf - a collection of data types where only one of the kinds can be used (a.k.a. enum)"""

    kinds: list[PrimitiveType | ADT | Reference] = []


class Enum(AbstractCollection):
    """Enum: a unique collection of primitives"""

    base_types: list[Type[PrimitiveType]] = []
    literals: set[Any] = set()


class StructField(BaseModel):
    """Structure field: type + additional info"""

    data_type: PrimitiveType | ADT | Reference
    description: str | None = None
    is_required: bool = False
    min_ver: str | None = None
    max_ver: str | None = None


class Struct(ADT):
    """Struct/Object"""

    fields: dict[str, StructField] = {}
    additional_fields: PrimitiveType | ADT | None = None
    pattern_properties: dict[str, PrimitiveType | ADT] | None = None


class Dictionary(ADT):
    """Simple dictionary with values of a single type"""

    value_type: PrimitiveType | ADT


class Array(AbstractList):
    """A pure list"""

    pass


class CommaSeparatedList(AbstractList):
    """A list that is serialized comma separated"""

    pass


class Set(AbstractList):
    """A set of unique items"""

    pass


class JsonSchemaParser:
    """JsonSchema to internal DataModel converter"""

    def parse(
        self, schema, ignore_read_only: bool = False
    ) -> ty.Tuple[ADT | None, list[ADT]]:
        """Parse JsonSchema object into internal DataModel"""
        results: list[ADT] = []
        res = self.parse_schema(
            schema, results, ignore_read_only=ignore_read_only
        )
        return (res, results)

    def parse_schema(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        min_ver: str | None = None,
        max_ver: str | None = None,
        ignore_read_only: bool | None = False,
    ) -> PrimitiveType | ADT:
        type_ = schema.get("type")
        if "enum" in schema:
            return self.parse_enum(
                schema,
                results,
                name=name,
                parent_name=parent_name,
                ignore_read_only=ignore_read_only,
            )
        if isinstance(type_, list):
            return self.parse_typelist(
                schema,
                results,
                name=name,
                parent_name=parent_name,
                ignore_read_only=ignore_read_only,
            )
        if isinstance(type_, str):
            if type_ == "object":
                return self.parse_object(
                    schema,
                    results,
                    name=name,
                    parent_name=parent_name,
                    min_ver=min_ver,
                    max_ver=max_ver,
                    ignore_read_only=ignore_read_only,
                )
            if type_ == "array":
                return self.parse_array(
                    schema,
                    results,
                    name=name,
                    parent_name=parent_name,
                    ignore_read_only=ignore_read_only,
                )
            if type_ == "string":
                obj = ConstraintString(**schema)
                # todo: set obj props
                return obj
            if type_ == "integer":
                obj = ConstraintInteger(**schema)
                # todo: set obj props
                return obj
            if type_ == "number":
                obj = ConstraintNumber(**schema)
                # todo: set obj props
                return obj
            if type_ == "boolean":
                obj = PrimitiveBoolean()
                # todo: set obj props
                return obj
            if type_ == "null":
                obj = PrimitiveNull()
                return obj
        if "oneOf" in schema:
            return self.parse_oneOf(
                schema,
                results,
                name=name,
                parent_name=parent_name,
                ignore_read_only=ignore_read_only,
            )
        if "allOf" in schema:
            return self.parse_allOf(
                schema,
                results,
                name=name,
                parent_name=parent_name,
                ignore_read_only=ignore_read_only,
            )
        if not type_ and "properties" in schema:
            # Sometimes services forget to set "type=object"
            return self.parse_object(
                schema,
                results,
                name=name,
                parent_name=parent_name,
                min_ver=min_ver,
                max_ver=max_ver,
                ignore_read_only=ignore_read_only,
            )
        if schema == {}:
            # `{}` is `Any` according to jsonschema
            return PrimitiveAny()
        if not type_ and "format" in schema:
            return ConstraintString(**schema)
        raise RuntimeError("Cannot determine type for %s", schema)

    def parse_object(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        min_ver: str | None = None,
        max_ver: str | None = None,
        ignore_read_only: bool | None = False,
    ):
        """Parse `object` schema

        Do basic parsing of the jsonschema that has `"type": "object"` in the
        root. In real life there might be `oneOf`,  `anyOf`, `not`,
        `dependentRequired`, `dependendSchemas`, `if-then-else` underneath. For
        now oneOf are supported by building an Enum ouf of this object
        when none of `properties`, `additional_properties`,
        `pattern_properties` are present. `anyOf` elemenst are merged into a
        single schema that is then parsed.

        The more complex validation rules (`"properties": ..., "oneOf":
        [{"required": []}, "required": []]`) are ignored.

        `if-then-else` are ignored since their main purpose is data validation
        and not the schema definition.
        """
        obj: ADT | None = None
        properties = schema.get("properties")
        additional_properties = schema.get("additionalProperties")
        additional_properties_type: PrimitiveType | ADT | None = None
        pattern_properties = schema.get("patternProperties")
        pattern_props: dict[str, PrimitiveType | ADT] | None = {}
        required = schema.get("required", [])
        os_ext: dict = schema.get("x-openstack", {})
        min_ver = os_ext.get("min-ver", min_ver)
        max_ver = os_ext.get("max-ver", max_ver)
        if properties:
            # `"type": "object", "properties": {...}}`
            obj = Struct()
            for k, v in properties.items():
                if k == "additionalProperties" and isinstance(v, bool):
                    # Some schemas (in keystone) are Broken
                    continue
                if ignore_read_only and v.get("readOnly", False):
                    continue
                data_type = self.parse_schema(
                    v,
                    results,
                    name=k,
                    parent_name=name,
                    min_ver=min_ver,
                    max_ver=max_ver,
                    ignore_read_only=ignore_read_only,
                )
                ref = getattr(data_type, "reference", None)
                if ref:
                    field = StructField(data_type=ref)
                else:
                    field = StructField(
                        data_type=data_type,
                    )

                field.description = v.get("description")
                if k in required:
                    field.is_required = True
                if min_ver:
                    field.min_ver = min_ver
                if max_ver:
                    field.max_ver = max_ver
                obj.fields[k] = field

        if additional_properties:
            # `"type": "object", "additional_properties": {...}}`
            if (
                isinstance(additional_properties, dict)
                and "type" in additional_properties
            ):
                additional_properties_type = self.parse_schema(
                    additional_properties,
                    results,
                    name=name,
                    min_ver=min_ver,
                    max_ver=max_ver,
                    ignore_read_only=ignore_read_only,
                )
            else:
                additional_properties_type = PrimitiveAny()

        if pattern_properties:
            # `"type": "object", "pattern_properties": {...}}`
            for key_pattern, value_type in pattern_properties.items():
                type_kind: PrimitiveType | ADT = self.parse_schema(
                    value_type,
                    results,
                    name=name,
                    min_ver=min_ver,
                    max_ver=max_ver,
                    ignore_read_only=ignore_read_only,
                )
                pattern_props[key_pattern] = type_kind  # type: ignore

        if obj:
            if additional_properties_type:
                # `"type": "object", "properties": {...}, "additional_properties": ...`
                obj.additional_fields = additional_properties_type
            if pattern_props:
                # `"type": "object", "properties": {...}, "pattern_properties": ...}`
                obj.pattern_properties = copy.deepcopy(pattern_props)
        else:
            if pattern_props and not additional_properties_type:
                # `"type": "object", "pattern_properties": ...`
                if len(list(pattern_props.values())) == 1:
                    obj = Dictionary(
                        value_type=list(pattern_props.values())[0]
                    )
                else:
                    obj = Struct(pattern_properties=pattern_props)
            elif not pattern_props and additional_properties_type:
                # `"type": "object", "additional_properties": ...`
                obj = Dictionary(value_type=additional_properties_type)
            else:
                if "oneOf" in schema:
                    # `"type": "object", "oneOf": []`
                    return self.parse_oneOf(
                        schema,
                        results,
                        name=name,
                        parent_name=parent_name,
                        ignore_read_only=ignore_read_only,
                    )
                elif "allOf" in schema:
                    # `"type": "object", "anyOf": []`
                    return self.parse_allOf(
                        schema,
                        results,
                        name=name,
                        parent_name=parent_name,
                        ignore_read_only=ignore_read_only,
                    )

                # `{"type": "object"}`
                obj = Dictionary(value_type=PrimitiveAny())
        if not obj:
            raise RuntimeError("Object %s is not supported", schema)

        if name:
            obj.reference = Reference(
                name=name, type=obj.__class__, hash_=dicthash_(schema)
            )

        if obj:
            obj.description = schema.get("description")
            if (
                obj.reference
                and f"{obj.reference.name}{obj.reference.type}"
                in [
                    f"{x.reference.name}{x.reference.type}"
                    for x in results
                    if x.reference
                ]
            ):
                if obj.reference in [
                    x.reference for x in results if x.reference
                ]:
                    # This is already same object - we have luck and can
                    # de-duplicate structures. It is at the moment the case in
                    # `image.metadef.namespace` with absolutely same `items`
                    # object present few times
                    pass
                else:
                    # Structure with the same name is already present. Prefix the
                    # new one with the parent name
                    if parent_name and name:
                        new_name = parent_name + "_" + name

                        if Reference(
                            name=new_name, type=obj.reference.type
                        ) in [x.reference for x in results]:
                            raise NotImplementedError
                        else:
                            obj.reference.name = new_name
            results.append(obj)
        return obj

    def parse_oneOf(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        ignore_read_only: bool | None = False,
    ):
        obj = OneOfType()
        for kind in schema.get("oneOf"):
            kind_schema = common._deep_merge(schema, kind)
            kind_schema.pop("oneOf")
            # todo: merge base props into the kind
            kind_type = self.parse_schema(
                kind_schema,
                results,
                name=name,
                ignore_read_only=ignore_read_only,
            )
            if not kind_type:
                raise NotImplementedError
            ref: Reference | None = getattr(kind_type, "reference", None)
            if ref:
                obj.kinds.append(ref)
            else:
                obj.kinds.append(kind_type)
        if name:
            obj.reference = Reference(
                name=name, type=obj.__class__, hash_=dicthash_(schema)
            )
        results.append(obj)
        return obj

    def parse_typelist(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        ignore_read_only: bool | None = False,
    ):
        if len(schema.get("type")) == 1:
            # Bad schema with type being a list of 1 entry
            schema["type"] = schema["type"][0]
            obj = self.parse_schema(
                schema,
                results,
                name=name,
                ignore_read_only=ignore_read_only,
            )
            return obj

        obj = OneOfType()

        for kind_type in schema.get("type"):
            kind_schema = copy.deepcopy(schema)
            kind_schema["type"] = kind_type
            kind_type = self.parse_schema(
                kind_schema,
                results,
                name=name,
                ignore_read_only=ignore_read_only,
            )
            ref = getattr(kind_type, "reference", None)
            if ref:
                obj.kinds.append(ref)
            else:
                obj.kinds.append(kind_type)
        if name:
            obj.reference = Reference(
                name=name, type=obj.__class__, hash_=dicthash_(schema)
            )
        results.append(obj)
        return obj

    def parse_array(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        ignore_read_only: bool | None = False,
    ):
        # todo: decide whether some constraints can be under items
        item_type = self.parse_schema(
            schema.get("items", {"type": "string"}),
            results,
            name=name,
            ignore_read_only=ignore_read_only,
        )
        ref = getattr(item_type, "reference", None)
        if ref:
            obj = Array(item_type=ref)
        else:
            obj = Array(item_type=item_type)
        if name:
            obj.reference = Reference(
                name=name, type=obj.__class__, hash_=dicthash_(schema)
            )
        results.append(obj)
        return obj

    def parse_enum(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        ignore_read_only: bool | None = False,
    ):
        # todo: decide whether some constraints can be under items
        literals = schema.get("enum")
        obj = Enum(literals=literals, base_types=[])
        literal_types = set([type(x) for x in literals])
        for literal_type in literal_types:
            if literal_type is str:
                obj.base_types.append(ConstraintString)
            elif literal_type is int:
                obj.base_types.append(ConstraintInteger)
            elif literal_type is bool:
                obj.base_types.append(PrimitiveBoolean)

        if name:
            obj.reference = Reference(
                name=name, type=obj.__class__, hash_=dicthash_(schema)
            )
        results.append(obj)
        return obj

    def parse_allOf(
        self,
        schema,
        results: list[ADT],
        name: str | None = None,
        parent_name: str | None = None,
        ignore_read_only: bool | None = False,
    ):
        sch = copy.deepcopy(schema)
        sch.pop("allOf")
        for kind in schema.get("allOf"):
            sch = common._deep_merge(sch, kind)
        obj = self.parse_schema(
            sch, results, name=name, ignore_read_only=ignore_read_only
        )
        if not obj:
            raise NotImplementedError
        # if name:
        #    obj.reference = Reference(name=name, type=obj.__class__)
        # results.append(obj)
        return obj


class RequestParameter(BaseModel):
    """OpenAPI Request parameter DataType wrapper"""

    name: str
    location: str
    data_type: PrimitiveType | ADT
    description: str | None = None
    is_required: bool = False
    is_flag: bool = False


class OpenAPISchemaParser(JsonSchemaParser):
    """OpenAPI to internal DataModel converter"""

    def parse_parameter(self, schema) -> RequestParameter:
        """Parse OpenAPI request parameter into internal DataModel"""
        param_name = schema.get("name")
        param_location = schema.get("in")
        param_schema = schema.get("schema")
        param_typ = param_schema.get("type")
        dt: PrimitiveType | ADT | None = None
        if isinstance(param_typ, list) and "null" in param_typ:
            param_typ.remove("null")
            if len(param_typ) == 1:
                param_typ = param_typ[0]
        if param_typ == "string":
            # NOTE: this is commented out so far since most of enums are just
            # too wrong to treat them as enums here
            # if "enum" in param_schema:
            #     dt = Enum(literals=param_schema["enum"], base_types=[ConstraintString])
            # else:
            dt = ConstraintString(**param_schema)
        elif param_typ == "number":
            dt = ConstraintNumber(**param_schema)
        elif param_typ == "integer":
            dt = ConstraintInteger(**param_schema)
        elif param_typ == "boolean":
            dt = PrimitiveBoolean(**param_schema)
        elif param_typ == "null":
            dt = PrimitiveNull(**param_schema)
        elif param_typ == "array":
            try:
                items_type = param_schema.get("items").get("type")
            except Exception:
                logging.exception("Broken array data: %s", param_schema)
                raise
            style = schema.get("style", "form")
            explode = schema.get("explode", True)
            if items_type == "string":
                if style == "form" and not explode:
                    dt = CommaSeparatedList(item_type=ConstraintString())
                elif style == "form" and explode:
                    dt = Set(item_type=ConstraintString())
                else:
                    raise NotImplementedError(
                        "Parameter serialization %s not supported" % schema
                    )

        elif isinstance(param_typ, list):
            # Param type can be anything. Process supported combinations first
            if param_location == "query" and param_name == "limit":
                dt = ConstraintInteger(minimum=0)
            elif param_location == "query" and sorted(
                ["string", "boolean"]
            ) == sorted(param_typ):
                dt = PrimitiveBoolean()
            elif param_location == "query" and sorted(
                ["string", "integer"]
            ) == sorted(param_typ):
                dt = ConstraintInteger(**param_schema)
            elif param_location == "query" and sorted(
                ["string", "number"]
            ) == sorted(param_typ):
                dt = ConstraintNumber(**param_schema)

        if isinstance(dt, ADT):
            # Set reference into the data_type so that it doesn't mess with main body types
            dt.reference = Reference(
                name=param_name, type=RequestParameter, hash_=dicthash_(schema)
            )

        is_flag: bool = False
        os_ext = schema.get("x-openstack", {})
        if not isinstance(os_ext, dict):
            raise RuntimeError(f"x-openstack must be a dictionary in {schema}")
        if "is-flag" in os_ext:
            is_flag = os_ext["is-flag"]

        if dt:
            return RequestParameter(
                name=param_name,
                location=param_location,
                data_type=dt,
                description=schema.get("description"),
                is_required=schema.get("required", False),
                is_flag=is_flag,
            )
        raise NotImplementedError("Parameter %s is not covered yet" % schema)

        raise RuntimeError("Parameter %s is not supported yet" % schema)
