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
import logging
import re
from typing import Type, Any, Generator, Tuple

from pydantic import BaseModel

from codegenerator.common import BasePrimitiveType
from codegenerator.common import BaseCombinedType
from codegenerator.common import BaseCompoundType
from codegenerator import model
from codegenerator import common


class Boolean(BasePrimitiveType):
    """Basic Boolean"""

    type_hint: str = "bool"
    imports: set[str] = set([])
    clap_macros: set[str] = set(["action=clap::ArgAction::Set"])
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    def get_sample(self):
        return "false"


class Number(BasePrimitiveType):
    format: str | None = None
    imports: set[str] = set([])
    clap_macros: set[str] = set()
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    @property
    def type_hint(self):
        if self.format == "float":
            return "f32"
        elif self.format == "double":
            return "f64"
        else:
            return "f32"

    def get_sample(self):
        return "123"


class Integer(BasePrimitiveType):
    format: str | None = None
    imports: set[str] = set([])
    clap_macros: set[str] = set()
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    @property
    def type_hint(self):
        if self.format == "int32":
            return "i32"
        elif self.format == "int64":
            return "i64"
        return "i32"

    def get_sample(self):
        return "123"


class Null(BasePrimitiveType):
    type_hint: str = "Value"
    imports: set[str] = set(["serde_json::Value"])
    builder_macros: set[str] = set(['default = "Value::Null"'])
    clap_macros: set[str] = set()
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    def get_sample(self):
        return "Value::Null"


class String(BasePrimitiveType):
    format: str | None = None
    type_hint: str = "String"
    builder_macros: set[str] = set(["setter(into)"])

    # NOTE(gtema): it is not possible to override field with computed
    # property, thus it must be a property here
    @property
    def imports(self) -> set[str]:
        return set([])

    def get_sample(self):
        return '"foo"'


class JsonValue(BasePrimitiveType):
    type_hint: str = "Value"
    imports: set[str] = set(["serde_json::Value"])
    builder_macros: set[str] = set(["setter(into)"])

    def get_sample(self):
        return "json!({})"


class Option(BaseCombinedType):
    base_type: str = "Option"
    item_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    @property
    def type_hint(self):
        return f"Option<{self.item_type.type_hint}>"

    @property
    def lifetimes(self):
        return self.item_type.lifetimes

    @property
    def imports(self):
        return self.item_type.imports

    @property
    def builder_macros(self):
        macros = set(["setter(into)"])
        wrapped_macros = self.item_type.builder_macros
        if "private" in wrapped_macros:
            macros = wrapped_macros
        return macros

    @property
    def clap_macros(self):
        return self.item_type.clap_macros

    def get_sample(self):
        return self.item_type.get_sample()


class Array(BaseCombinedType):
    base_type: str = "vec"
    item_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType

    @property
    def type_hint(self):
        return f"Vec<{self.item_type.type_hint}>"

    @property
    def lifetimes(self):
        return self.item_type.lifetimes

    @property
    def imports(self):
        return self.item_type.imports

    @property
    def builder_macros(self):
        macros = set(["setter(into)"])
        return macros

    def get_sample(self):
        return (
            "Vec::from(["
            + self.item_type.get_sample()
            + (".into()" if isinstance(self.item_type, String) else "")
            + "])"
        )

    @property
    def clap_macros(self) -> set[str]:
        return self.item_type.clap_macros


class CommaSeparatedList(BaseCombinedType):
    item_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType

    @property
    def type_hint(self):
        return f"CommaSeparatedList<{self.item_type.type_hint}>"

    @property
    def lifetimes(self):
        return self.item_type.lifetimes

    @property
    def imports(self):
        imports: set[str] = set([])
        imports.update(self.item_type.imports)
        return imports

    @property
    def clap_macros(self) -> set[str]:
        return set()


class BTreeSet(BaseCombinedType):
    item_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType
    builder_macros: set[str] = set(["setter(into)"])

    @property
    def type_hint(self):
        return f"BTreeSet<{self.item_type.type_hint}>"

    @property
    def lifetimes(self):
        return self.item_type.lifetimes

    @property
    def imports(self):
        imports = self.item_type.imports
        imports.add("std::collections::BTreeSet")
        return imports


class Dictionary(BaseCombinedType):
    base_type: str = "dict"
    value_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType


class StructField(BaseModel):
    local_name: str
    remote_name: str
    description: str | None = None
    data_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType
    is_optional: bool = True
    is_nullable: bool = False

    @property
    def type_hint(self):
        typ_hint = self.data_type.type_hint
        if self.is_optional:
            typ_hint = f"Option<{typ_hint}>"
        return typ_hint


class Struct(BaseCompoundType):
    base_type: str = "struct"
    fields: dict[str, StructField] = {}
    field_type_class_: Type[StructField] | StructField = StructField
    additional_fields_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType | None = (
        None
    )

    @property
    def type_hint(self):
        return self.name + (
            f"<{', '.join(self.lifetimes)}>" if self.lifetimes else ""
        )

    @property
    def imports(self):
        imports: set[str] = set(["serde::Deserialize"])
        for field in self.fields.values():
            imports.update(field.data_type.imports)
        if self.additional_fields_type:
            imports.add("std::collections::BTreeMap")
            imports.update(self.additional_fields_type.imports)
        return imports

    @property
    def lifetimes(self):
        lifetimes_: set[str] = set()
        for field in self.fields.values():
            if field.data_type.lifetimes:
                lifetimes_.update(field.data_type.lifetimes)
        return lifetimes_

    @property
    def clap_macros(self) -> set[str]:
        return set()


class EnumKind(BaseModel):
    name: str
    description: str | None = None
    data_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType

    @property
    def type_hint(self):
        if isinstance(self.data_type, Struct):
            return self.data_type.name + self.data_type.static_lifetime
        return self.data_type.type_hint

    @property
    def clap_macros(self) -> set[str]:
        return set()


class Enum(BaseCompoundType):
    base_type: str = "enum"
    kinds: dict[str, EnumKind]
    literals: list[Any] | None = None
    _kind_type_class = EnumKind

    @property
    def type_hint(self):
        return self.name + (
            f"<{', '.join(self.lifetimes)}>" if self.lifetimes else ""
        )

    @property
    def imports(self):
        imports: set[str] = set()
        for kind in self.kinds.values():
            imports.update(kind.data_type.imports)
        return imports

    @property
    def lifetimes(self):
        lifetimes_: set[str] = set()
        for kind in self.kinds.values():
            if kind.data_type.lifetimes:
                lifetimes_.update(kind.data_type.lifetimes)
        return lifetimes_

    @property
    def clap_macros(self) -> set[str]:
        return set()


class StringEnum(BaseCompoundType):
    base_type: str = "enum"
    variants: dict[str, set[str]] = {}
    imports: set[str] = set([])
    lifetimes: set[str] = set()
    derive_container_macros: str = (
        "#[derive(Debug, Deserialize, Clone, Serialize)]"
    )
    builder_container_macros: str | None = None
    serde_container_macros: str | None = None  # "#[serde(untagged)]"
    serde_macros: set[str] | None = None
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    @property
    def type_hint(self):
        """Get type hint"""
        return self.name

    @property
    def clap_macros(self) -> set[str]:
        """ "Return clap macros"""
        return set()

    def get_sample(self):
        """Generate sample data"""
        variant = list(self.variants.keys())[0]
        return f"{self.name}::{variant}"

    def variant_serde_macros(self, variant: str):
        """Return serde macros"""
        return (
            "#[serde("
            + ", ".join([f'rename="{x}"' for x in self.variants[variant]])
            + ")]"
        )


class RequestParameter(BaseModel):
    """OpenAPI request parameter in the Rust SDK form"""

    remote_name: str
    local_name: str
    location: str
    data_type: BaseCombinedType | BasePrimitiveType
    description: str | None = None
    is_required: bool = False
    setter_name: str | None = None
    setter_type: str | None = None

    @property
    def type_hint(self):
        if not self.is_required and not isinstance(self.data_type, BTreeSet):
            return f"Option<{self.data_type.type_hint}>"
        return self.data_type.type_hint

    @property
    def lifetimes(self):
        return self.data_type.lifetimes


class TypeManager:
    """Rust type manager

    The class is responsible for converting ADT models into types suitable
    for Rust.
    """

    models: list = []
    refs: dict[
        model.Reference,
        BasePrimitiveType | BaseCombinedType | BaseCompoundType,
    ] = {}
    parameters: dict[str, Type[RequestParameter] | RequestParameter] = {}

    base_primitive_type_mapping: dict[
        Type[model.PrimitiveType],
        Type[BasePrimitiveType] | Type[BaseCombinedType],
    ] = {
        model.PrimitiveString: String,
        model.ConstraintString: String,
        model.PrimitiveNumber: Number,
        model.ConstraintNumber: Number,
        model.ConstraintInteger: Integer,
        model.PrimitiveBoolean: Boolean,
        model.PrimitiveNull: Null,
        model.PrimitiveAny: JsonValue,
    }

    primitive_type_mapping: dict[
        Type[model.PrimitiveType],
        Type[BasePrimitiveType] | Type[BaseCombinedType],
    ]

    data_type_mapping: dict[
        Type[model.ADT], Type[BaseCombinedType] | Type[BaseCompoundType]
    ]
    base_data_type_mapping: dict[
        Type[model.ADT], Type[BaseCombinedType] | Type[BaseCompoundType]
    ] = {
        model.Dictionary: Dictionary,
        model.Enum: Enum,
        model.Struct: Struct,
        model.Array: Array,
        model.CommaSeparatedList: CommaSeparatedList,
        model.Set: BTreeSet,
    }
    request_parameter_class: Type[RequestParameter] = RequestParameter
    option_type_class: Type[Option] | Option = Option
    string_enum_class: Type[StringEnum] | StringEnum = StringEnum

    def __init__(self):
        self.models = []
        self.refs = {}
        self.parameters = {}

        # Set base mapping entries into the data_type_mapping
        for k, v in self.base_primitive_type_mapping.items():
            if k not in self.primitive_type_mapping:
                self.primitive_type_mapping[k] = v

        for k, v in self.base_data_type_mapping.items():
            if k not in self.data_type_mapping:
                self.data_type_mapping[k] = v

    def get_local_attribute_name(self, name: str) -> str:
        """Get localized attribute name"""
        attr_name = "_".join(
            x.lower() for x in re.split(common.SPLIT_NAME_RE, name)
        )
        if attr_name in ["type", "self", "enum", "ref"]:
            attr_name = f"_{attr_name}"
        return attr_name

    def get_remote_attribute_name(self, name: str) -> str:
        """Get remote attribute name

        This method can be used on the client side to be able to override
        remote attribute name as a local name on the SDK side.
        """
        return name

    def get_model_name(self, model_ref: model.Reference | None) -> str:
        """Get the localized model type name"""
        if not model_ref:
            return "Request"
        name = "".join(
            x.capitalize()
            for x in re.split(common.SPLIT_NAME_RE, model_ref.name)
        )
        return name

    def _get_adt_by_reference(self, model_ref):
        for model_ in self.models:
            if model_.reference == model_ref:
                return model_
        raise RuntimeError("Cannot find reference %s" % model_ref)

    def convert_model(
        self,
        type_model: model.PrimitiveType | model.ADT | model.Reference,
    ) -> BasePrimitiveType | BaseCombinedType | BaseCompoundType:
        """Get local destination type from the ModelType"""
        # logging.debug("Get RustSDK type for %s", type_model)
        typ: BasePrimitiveType | BaseCombinedType | BaseCompoundType | None = (
            None
        )
        model_ref: model.Reference | None = None
        if isinstance(type_model, model.Reference):
            model_ref = type_model
            type_model = self._get_adt_by_reference(type_model)
        elif isinstance(type_model, model.ADT):
            # Direct composite type
            model_ref = type_model.reference
        else:
            # Primitive
            xtyp = self.primitive_type_mapping.get(type_model.__class__)
            if not xtyp:
                raise RuntimeError("No mapping for %s" % type_model)
            return xtyp(**type_model.model_dump())

        # Composite/Compound type
        if model_ref and model_ref in self.refs:
            return self.refs[model_ref]
        if isinstance(type_model, model.Array):
            typ = self._get_array_type(type_model)
        elif isinstance(type_model, model.Struct):
            typ = self._get_struct_type(type_model)
        elif isinstance(type_model, model.OneOfType):
            typ = self._get_one_of_type(type_model)
        elif isinstance(type_model, model.Dictionary):
            typ = self.data_type_mapping[model.Dictionary](
                value_type=self.convert_model(type_model.value_type)
            )
        elif isinstance(type_model, model.CommaSeparatedList):
            typ = self.data_type_mapping[model.CommaSeparatedList](
                item_type=self.convert_model(type_model.item_type)
            )
        elif isinstance(type_model, model.Set):
            typ = self.data_type_mapping[model.Set](
                item_type=self.convert_model(type_model.item_type)
            )
        elif isinstance(type_model, model.Enum):
            if len(type_model.base_types) > 1:
                if model.PrimitiveBoolean in type_model.base_types:
                    # enum literals supporting also bools are most likely
                    # bool + string -> just keep bool on the Rust side
                    typ = Boolean()
                else:
                    raise RuntimeError(
                        f"Rust model does not support multitype enums yet {type_model}"
                    )
            elif len(type_model.base_types) == 1:
                base_type = type_model.base_types[0]
                if base_type is model.ConstraintString:
                    variants: dict[str, set[str]] = {}
                    try:
                        if None in type_model.literals:
                            # TODO(gtema): make parent nullable or add "null"
                            # as enum value
                            type_model.literals.remove(None)
                        for lit in set(x.lower() for x in type_model.literals):
                            val = "".join(
                                [
                                    x.capitalize()
                                    for x in re.split(
                                        common.SPLIT_NAME_RE, lit
                                    )
                                ]
                            )
                            if val and val[0].isdigit():
                                val = "_" + val
                            vals = variants.setdefault(val, set())
                            for orig_val in type_model.literals:
                                if orig_val.lower() == lit:
                                    vals.add(orig_val)

                        typ = self.string_enum_class(
                            name=self.get_model_name(type_model.reference),
                            variants=variants,
                        )
                    except Exception:
                        logging.exception(
                            "Error processing enum: %s", type_model
                        )
                elif base_type is model.ConstraintInteger:
                    typ = self.primitive_type_mapping[
                        model.ConstraintInteger
                    ]()
                elif base_type is model.PrimitiveBoolean:
                    typ = self.primitive_type_mapping[model.PrimitiveBoolean]()

        if not typ:
            raise RuntimeError(
                "Cannot map model type %s to Rust type [%s]"
                % (type_model.__class__.__name__, type_model)
            )

        if not model_ref:
            model_ref = model.Reference(name="Body", type=typ.__class__)
        self.refs[model_ref] = typ
        return typ

    def _get_array_type(self, type_model: model.Array) -> Array:
        """Convert `model.Array` into corresponding Rust SDK model"""
        return self.data_type_mapping[model.Array](
            name=self.get_model_name(type_model.reference),
            item_type=self.convert_model(type_model.item_type),
        )

    def _get_one_of_type(
        self, type_model: model.OneOfType
    ) -> BaseCompoundType | BaseCombinedType | BasePrimitiveType:
        """Convert `model.OneOfType` into Rust model"""
        kinds: list[dict] = []
        is_nullable: bool = False
        result_data_type = None
        for kind in type_model.kinds:
            if isinstance(kind, model.PrimitiveNull):
                # Remove null from candidates and instead wrap with Option
                is_nullable = True
                continue
            kind_type = self.convert_model(kind)
            is_type_already_present = False
            for processed_kind_type in kinds:
                if (
                    isinstance(kind_type, BasePrimitiveType)
                    and processed_kind_type["local"] == kind_type
                ):
                    logging.debug(
                        "Simplifying oneOf with same mapped type %s [%s]",
                        kind,
                        type_model,
                    )
                    is_type_already_present = True
                    break
            if not is_type_already_present:
                kinds.append(
                    {
                        "model": kind,
                        "local": kind_type,
                        "class": kind_type.__class__,
                    }
                )

        # Simplify certain oneOf combinations
        self._simplify_oneof_combinations(type_model, kinds)

        if len(kinds) == 2:
            list_type = [
                x["local"]
                for x in kinds
                if x["class"] == self.data_type_mapping[model.Array]
            ]
            if list_type:
                lt: BaseCombinedType = list_type[0]
                # Typ + list[Typ] => Vec<Typ>
                item_type = [
                    x["local"]
                    for x in kinds
                    if x["class"] != self.data_type_mapping[model.Array]
                ][0]
                if item_type.__class__ == lt.item_type.__class__:
                    result_data_type = self.data_type_mapping[model.Array](
                        item_type=item_type,
                        description=sanitize_rust_docstrings(
                            type_model.description
                        ),
                    )
                    # logging.debug("Replacing Typ + list[Typ] with list[Typ]")
        elif len(kinds) == 1:
            result_data_type = kinds[0]["local"]

        if not result_data_type:
            enum_class = self.data_type_mapping[model.Enum]
            result_data_type = enum_class(
                name=self.get_model_name(type_model.reference), kinds={}
            )
            cnt: int = 0
            for kind_data in kinds:
                cnt += 1
                kind_data_type = kind_data["local"]
                kind_description: str | None = None
                if isinstance(kind_data["model"], model.ADT):
                    kind_name = self.get_model_name(kind_data["model"])
                    kind_description = kind_data["model"].description
                else:
                    kind_name = f"F{cnt}"
                enum_kind = enum_class._kind_type_class(
                    name=kind_name,
                    description=sanitize_rust_docstrings(kind_description),
                    data_type=kind_data_type,
                )
                result_data_type.kinds[enum_kind.name] = enum_kind

        if is_nullable:
            result_data_type = self.option_type_class(
                item_type=result_data_type
            )

        return result_data_type

    def _get_struct_type(self, type_model: model.Struct) -> Struct:
        """Convert model.Struct into Rust `Struct`"""
        struct_class = self.data_type_mapping[model.Struct]
        mod = struct_class(
            name=self.get_model_name(type_model.reference),
            description=sanitize_rust_docstrings(type_model.description),
        )
        field_class = mod.field_type_class_
        for field_name, field in type_model.fields.items():
            is_nullable: bool = False
            field_data_type = self.convert_model(field.data_type)
            if isinstance(field_data_type, self.option_type_class):
                # Unwrap Option into "is_nullable" NOTE: but perhaps
                # Option<Option> is better (not set vs set explicitly to None
                # )
                is_nullable = True
                if isinstance(field_data_type.item_type, Array):
                    # Unwrap Option<Option<Vec...>>
                    field_data_type = field_data_type.item_type
            f = field_class(
                local_name=self.get_local_attribute_name(field_name),
                remote_name=self.get_remote_attribute_name(field_name),
                description=sanitize_rust_docstrings(field.description),
                data_type=field_data_type,
                is_optional=not field.is_required,
                is_nullable=is_nullable,
            )
            mod.fields[field_name] = f
        if type_model.additional_fields:
            definition = type_model.additional_fields
            # Structure allows additional fields
            if isinstance(definition, bool):
                mod.additional_fields_type = self.primitive_type_mapping[
                    model.PrimitiveAny
                ]
            else:
                mod.additional_fields_type = self.convert_model(definition)
        return mod

    def _simplify_oneof_combinations(self, type_model, kinds):
        """Simplify certain known oneOf combinations"""
        kinds_classes = [x["class"] for x in kinds]
        string_klass = self.primitive_type_mapping[model.ConstraintString]
        number_klass = self.primitive_type_mapping[model.ConstraintNumber]
        integer_klass = self.primitive_type_mapping[model.ConstraintInteger]
        boolean_klass = self.primitive_type_mapping[model.PrimitiveBoolean]
        dict_klass = self.data_type_mapping[model.Dictionary]
        enum_name = type_model.reference.name if type_model.reference else None
        if string_klass in kinds_classes and number_klass in kinds_classes:
            # oneOf [string, number] => string
            for typ in list(kinds):
                if typ["class"] == number_klass:
                    kinds.remove(typ)
        elif string_klass in kinds_classes and integer_klass in kinds_classes:
            if enum_name and (
                enum_name.endswith("size") or enum_name.endswith("count")
            ):
                # XX_size or XX_count is clearly an integer
                for typ in list(kinds):
                    if typ["class"] == string_klass:
                        kinds.remove(typ)
            else:
                # oneOf [string, integer] => string
                # Reason: compute.server.flavorRef is string or integer. For
                # simplicity keep string
                for typ in list(kinds):
                    if typ["class"] == integer_klass:
                        kinds.remove(typ)
        elif string_klass in kinds_classes and boolean_klass in kinds_classes:
            # oneOf [string, boolean] => boolean
            for typ in list(kinds):
                if typ["class"] == string_klass:
                    kinds.remove(typ)
        elif string_klass in kinds_classes and dict_klass in kinds_classes:
            # oneOf [string, dummy object] => JsonValue
            # Simple string can be easily represented by JsonValue
            kinds.clear()
            jsonval_klass = self.primitive_type_mapping[model.PrimitiveAny]
            kinds.append({"local": jsonval_klass(), "class": jsonval_klass})

    def set_models(self, models):
        """Process (translate) ADT models into Rust SDK style"""
        self.models = models
        self.refs = {}
        unique_model_names: set[str] = set()
        for model_ in models:
            model_data_type = self.convert_model(model_)
            if not isinstance(model_data_type, BaseCompoundType):
                continue
            name = getattr(model_data_type, "name", None)
            if name and name in unique_model_names:
                # There is already a model with this name. Try adding suffix from datatype name
                new_name = name + model_data_type.__class__.__name__
                if new_name not in unique_model_names:
                    # New name is still unused
                    model_data_type.name = new_name
                    unique_model_names.add(new_name)
                else:
                    raise RuntimeError(
                        "Model name %s is already present" % name
                    )
            elif name:
                unique_model_names.add(name)

    def get_subtypes(self):
        """Get all subtypes excluding TLA"""
        for k, v in self.refs.items():
            if (
                k
                and isinstance(v, (Enum, Struct, StringEnum))
                and k.name != "Body"
            ):
                yield v
            elif (
                k
                and k.name != "Body"
                and isinstance(v, self.option_type_class)
            ):
                if isinstance(v.item_type, Enum):
                    yield v.item_type

    def get_root_data_type(self):
        """Get TLA type"""
        for k, v in self.refs.items():
            if not k or (k.name == "Body" and isinstance(v, Struct)):
                if isinstance(v.fields, dict):
                    # There might be tuple Struct (with
                    # fields as list)
                    field_names = list(v.fields.keys())
                    if (
                        len(field_names) == 1
                        and v.fields[field_names[0]].is_optional
                    ):
                        # A body with only field can not normally be optional
                        logging.warning(
                            "Request body with single root field cannot be optional"
                        )
                        v.fields[field_names[0]].is_optional = False
                return v
        # No root has been found, make a dummy one
        root = self.data_type_mapping[model.Struct](name="Request")
        return root

    def get_imports(self):
        """Get complete set of additional imports required by all models in scope"""
        imports: set[str] = set()
        for item in self.refs.values():
            imports.update(item.imports)
        for param in self.parameters.values():
            imports.update(param.data_type.imports)
        return imports

    def get_request_static_lifetimes(self, request_model: Struct):
        """Return static lifetimes of the Structure"""
        lifetimes = request_model.lifetimes
        for param in self.parameters.values():
            lt = param.lifetimes
            if lt:
                lifetimes.update(lt)
        if lifetimes:
            return f"<{', '.join(lifetimes)}>"
        return ""

    def subtype_requires_private_builders(self, subtype) -> bool:
        """Return `True` if type require private builder"""
        if not isinstance(subtype, self.data_type_mapping[model.Struct]):
            return False
        for field in subtype.fields.values():
            if "private" in field.builder_macros:
                return True
        return False

    def set_parameters(self, parameters: list[model.RequestParameter]) -> None:
        """Set OpenAPI operation parameters into typemanager for conversion"""
        for parameter in parameters:
            data_type = self.convert_model(parameter.data_type)
            # if not parameter.is_required:
            #     data_type = Option(item_type=data_type)
            param = self.request_parameter_class(
                remote_name=self.get_remote_attribute_name(parameter.name),
                local_name=self.get_local_attribute_name(parameter.name),
                data_type=data_type,
                location=parameter.location,
                description=sanitize_rust_docstrings(parameter.description),
                is_required=parameter.is_required,
            )
            if isinstance(data_type, CommaSeparatedList):
                param.setter_name = param.local_name
                param.setter_type = "csv"
            if isinstance(data_type, BTreeSet):
                param.setter_name = param.local_name
                param.setter_type = "set"
            if isinstance(data_type, Array):
                param.setter_name = param.local_name
                param.setter_type = "list"

            self.parameters[param.local_name] = param

    def get_parameters(
        self, location: str
    ) -> Generator[Tuple[str, Type[RequestParameter]], None, None]:
        """Get parameters by location"""
        for k, v in self.parameters.items():
            if v.location == location:
                yield (k, v)


def sanitize_rust_docstrings(doc: str | None) -> str | None:
    """Sanitize the string to be a valid rust docstring"""
    if not doc:
        return None
    code_block_open: bool = False
    lines: list[str] = []
    for line in doc.split("\n"):
        if line.endswith("```"):
            if not code_block_open:
                # Rustdoc defaults to rust code for code blocks. To prevent
                # this explicitly add `text`
                code_block_open = True
                line = line + "text"
            else:
                code_block_open = False
        lines.append(line)
    return "\n".join(lines)


def get_operation_variants(spec: dict, operation_name: str):
    request_body = spec.get("requestBody")
    # List of operation variants (based on the body)
    operation_variants = []

    if request_body:
        content = request_body.get("content", {})
        json_body_schema = content.get("application/json", {}).get("schema")
        if json_body_schema:
            mime_type = "application/json"
            # response_def = json_body_schema
            if "oneOf" in json_body_schema:
                # There is a choice of bodies. It can be because of
                # microversion or an action (or both)
                # For action we should come here with operation_type="action" and operation_name must be the action name
                # For microversions we build body as enum
                # So now try to figure out what the discriminator is
                discriminator = json_body_schema.get("x-openstack", {}).get(
                    "discriminator"
                )
                if discriminator == "microversion":
                    logging.debug("Microversion discriminator for bodies")
                    for variant in json_body_schema["oneOf"]:
                        variant_spec = variant.get("x-openstack", {})
                        operation_variants.append(
                            {"body": variant, "mime_type": mime_type}
                        )
                    # operation_variants.extend([{"body": x} for x in json_body_schema(["oneOf"])])
                elif discriminator == "action":
                    # We are in the action. Need to find matching body
                    for variant in json_body_schema["oneOf"]:
                        variant_spec = variant.get("x-openstack", {})
                        if variant_spec.get("action-name") == operation_name:
                            discriminator = variant_spec.get("discriminator")
                            if (
                                "oneOf" in variant
                                and discriminator == "microversion"
                            ):
                                logging.debug(
                                    "Microversion discriminator for action bodies"
                                )
                                for subvariant in variant["oneOf"]:
                                    subvariant_spec = subvariant.get(
                                        "x-openstack", {}
                                    )
                                    operation_variants.append(
                                        {
                                            "body": subvariant,
                                            "mode": "action",
                                            "min-ver": subvariant_spec.get(
                                                "min-ver"
                                            ),
                                            "mime_type": mime_type,
                                        }
                                    )
                            else:
                                logging.debug(
                                    "Action %s with %s", variant, discriminator
                                )
                                operation_variants.append(
                                    {
                                        "body": variant,
                                        "mode": "action",
                                        "min-ver": variant_spec.get("min-ver"),
                                        "mime_type": mime_type,
                                    }
                                )
                            break
                    if not operation_variants:
                        raise RuntimeError(
                            "Cannot find body specification for action %s"
                            % operation_name
                        )
            else:
                operation_variants.append(
                    {"body": json_body_schema, "mime_type": mime_type}
                )
        elif "application/octet-stream" in content:
            mime_type = "application/octet-stream"
            operation_variants.append({"mime_type": mime_type})
        elif "application/openstack-images-v2.1-json-patch" in content:
            mime_type = "application/openstack-images-v2.1-json-patch"
            operation_variants.append({"mime_type": mime_type})
        elif "application/json-patch+json" in content:
            mime_type = "application/json-patch+json"
            operation_variants.append({"mime_type": mime_type})
    else:
        # Explicitly register variant without body
        operation_variants.append({"body": None})

    return operation_variants
