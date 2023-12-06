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
from typing import Type

from pydantic import BaseModel

from codegenerator import common


class Reference(BaseModel):
    """Reference of the complex type to the occurence instance"""

    #: Name of the object that uses the type under reference
    name: str
    type: Type | None = None

    def __hash__(self):
        return hash((self.name, self.type))


class PrimitiveType(BaseModel):
    """Primitive Data Type stricture"""

    pass


class PrimitiveString(PrimitiveType):
    pass


class ConstraintString(PrimitiveString):
    format: str | None = None
    minLength: int | None = None
    maxLength: int | None = None
    pattern: str | None = None


class PrimitiveNumber(PrimitiveType):
    pass


class ConstraintNumber(PrimitiveNumber):
    format: str | None = None
    minimum: int | None = None
    maximum: int | None = None
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


class EnumCollection(AbstractCollection):
    """Enum: a unique collection of primitives"""

    literals: set[PrimitiveType] = set()


class StructField(BaseModel):
    """Structure field: type + additional info"""

    data_type: PrimitiveType | ADT | Reference
    description: str | None = None
    is_required: bool = False


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


class JsonSchemaParser:
    adts: list[ADT] = []

    def parse(self, schema):
        results: list[ADT] = []
        res = self.parse_schema(schema, results)
        return (res, results)

    def parse_schema(self, schema, results: list[ADT], name: str = None):
        # logging.debug("Parsing %s", schema)
        type_ = schema.get("type")
        if "oneOf" in schema:
            return self.parse_oneOf(schema, results, name=name)
        elif isinstance(type_, list):
            return self.parse_typelist(schema, results, name=name)
        elif isinstance(type_, str):
            if type_ == "object":
                return self.parse_object(schema, results, name=name)
            elif type_ == "array":
                return self.parse_array(schema, results, name=name)
            elif type_ == "string":
                obj = ConstraintString(**schema)
                # todo: set obj props
                return obj
            elif type_ == "integer":
                obj = ConstraintInteger(**schema)
                # todo: set obj props
                return obj
            elif type_ == "number":
                obj = ConstraintNumber(**schema)
                # todo: set obj props
                return obj
            elif type_ == "boolean":
                obj = PrimitiveBoolean()
                # todo: set obj props
                return obj
            elif type_ == "null":
                obj = PrimitiveNull()
                return obj
        elif schema == {}:
            return PrimitiveNull()
        raise RuntimeError("Cannot determine type for %s", schema)

    def parse_object(self, schema, results: list[ADT], name: str = None):
        obj: PrimitiveType | ADT = None
        properties = schema.get("properties")
        additional_properties = schema.get("additionalProperties")
        additional_properties_type: PrimitiveType | ADT | None = None
        pattern_properties = schema.get("patternProperties")
        pattern_props: dict[str, PrimitiveType | ADT] | None = {}
        required = schema.get("required", [])
        if properties:
            obj = Struct()
            for k, v in properties.items():
                data_type = self.parse_schema(v, results, name=k)
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
                obj.fields[k] = field
        if additional_properties:
            if (
                isinstance(additional_properties, dict)
                and "type" in additional_properties
            ):
                additional_properties_type = self.parse_schema(
                    additional_properties, results, name=name
                )
            else:
                additional_properties_type = PrimitiveAny()

        if pattern_properties:
            for key_pattern, value_type in pattern_properties.items():
                type_kind: PrimitiveType | ADT = self.parse_schema(
                    value_type, results, name=name
                )
                pattern_props[key_pattern] = type_kind

        if obj:
            if additional_properties_type:
                obj.additional_fields = additional_properties_type
            if pattern_props:
                obj.pattern_properties = copy.deepcopy(pattern_props)
        else:
            if pattern_props and not additional_properties_type:
                if len(list(pattern_props.values())) == 1:
                    obj = Dictionary(
                        value_type=list(pattern_props.values())[0]
                    )
                else:
                    obj = Struct(pattern_properties=pattern_props)
            elif not pattern_props and additional_properties_type:
                obj = Dictionary(value_type=additional_properties_type)
            else:
                obj = Dictionary(value_type=PrimitiveAny())
        if not obj:
            raise RuntimeError("Object %s is not supported", schema)

        if name:
            obj.reference = Reference(name=name, type=obj.__class__)

        if obj:
            obj.description = schema.get("description")
            results.append(obj)
        return obj

    def parse_oneOf(self, schema, results: list[ADT], name: str = None):
        obj = OneOfType()
        for kind in schema.get("oneOf"):
            kind_schema = common._deep_merge(schema, kind)
            kind_schema.pop("oneOf")
            # todo: merge base props into the kind
            kind_type = self.parse_schema(kind_schema, results, name=name)
            ref = getattr(kind_type, "reference", None)
            if ref:
                obj.kinds.append(ref)
            else:
                obj.kinds.append(kind_type)
        if name:
            obj.reference = Reference(name=name, type=obj.__class__)
        results.append(obj)
        return obj

    def parse_typelist(self, schema, results: list[ADT], name: str = None):
        obj = OneOfType()
        for kind_type in schema.get("type"):
            kind_schema = copy.deepcopy(schema)
            kind_schema["type"] = kind_type
            kind_type = self.parse_schema(kind_schema, results, name=name)
            ref = getattr(kind_type, "reference", None)
            if ref:
                obj.kinds.append(ref)
            else:
                obj.kinds.append(kind_type)
        if name:
            obj.reference = Reference(name=name, type=obj.__class__)
        results.append(obj)
        return obj

    def parse_array(self, schema, results: list[ADT], name: str = None):
        # todo: decide whether some constraints can be under items
        item_type = self.parse_schema(schema.get("items"), results, name=name)
        ref = getattr(item_type, "reference", None)
        if ref:
            obj = Array(item_type=ref)
        else:
            obj = Array(item_type=item_type)
        if name:
            obj.reference = Reference(name=name, type=obj.__class__)
        results.append(obj)
        return obj
