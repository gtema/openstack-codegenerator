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
from pathlib import Path
import subprocess
import re
from typing import Type

from codegenerator.base import BaseGenerator
from codegenerator import common
from codegenerator import model
from codegenerator.common import rust as common_rust
from codegenerator.common import BasePrimitiveType
from codegenerator.common import BaseCombinedType
from codegenerator.common import BaseCompoundType


BASIC_FIELDS = ["id", "name", "created_at", "updated_at"]


class BooleanFlag(common_rust.Boolean):
    """Boolean parameter that is represented as a CLI flag"""

    type_hint: str = "bool"
    clap_macros: set[str] = set(["action=clap::ArgAction::SetTrue"])


class String(common_rust.String):
    """CLI String type"""

    clap_macros: set[str] = set()
    original_data_type: BaseCompoundType | BaseCompoundType | None = None


class IntString(common.BasePrimitiveType):
    """CLI Integer or String"""

    imports: set[str] = set(["crate::common::IntString"])
    type_hint: str = "IntString"
    clap_macros: set[str] = set()


class NumString(common.BasePrimitiveType):
    """CLI Number or String"""

    imports: set[str] = set(["crate::common::NumString"])
    type_hint: str = "NumString"
    clap_macros: set[str] = set()


class BoolString(common.BasePrimitiveType):
    """CLI Boolean or String"""

    imports: set[str] = set(["crate::common::BoolString"])
    type_hint: str = "BoolString"
    clap_macros: set[str] = set()


class VecString(common.BasePrimitiveType):
    """CLI Vector of strings"""

    imports: set[str] = set(["crate::common::VecString"])
    type_hint: str = "VecString"
    clap_macros: set[str] = set()


class JsonValue(common_rust.JsonValue):
    """Arbitrary JSON value"""

    imports: set[str] = set(["crate::common::parse_json", "serde_json::Value"])
    clap_macros: set[str] = set(
        ['value_name="JSON"', "value_parser=parse_json"]
    )
    original_data_type: BaseCompoundType | BaseCompoundType | None = None


class StructInputField(common_rust.StructField):
    """Structure field of the CLI input"""

    additional_clap_macros: set[str] = set()

    @property
    def builder_macros(self):
        macros: set[str] = set([])
        if not isinstance(self.data_type, BaseCompoundType):
            macros.update(self.data_type.builder_macros)
        else:
            macros.add("setter(into)")
        if self.is_optional:
            macros.add("default")
        return f"#[builder({', '.join(sorted(macros))})]"

    @property
    def serde_macros(self):
        macros = set([])
        if self.local_name != self.remote_name:
            macros.add(f'rename="{self.remote_name}"')
        return f"#[serde({', '.join(sorted(macros))})]"

    @property
    def clap_macros(self):
        if isinstance(self.data_type, common_rust.Struct):
            # For substrucs (and maybe enums) we tell Clap to flatten subtype
            # instead of exposing attr itself
            return "#[command(flatten)]"
        macros = set(["long"])
        try:
            if self.data_type.clap_macros:
                macros.update(self.data_type.clap_macros)
            # i.e. CLI groups are managed through the code dynamically
            macros.update(self.additional_clap_macros)
        except Exception as ex:
            logging.exception("Error getting clap_macros for %s: %s", self, ex)
        return f"#[arg({', '.join(sorted(macros))})]"

    def clap_macros_ext(self, is_group: bool | None = None):
        if isinstance(self.data_type, common_rust.Struct):
            # For substrucs (and maybe enums) we tell Clap to flatten subtype
            # instead of exposing attr itself
            return "#[command(flatten)]"
        macros = set(["long"])
        if is_group and not self.is_optional:
            macros.add("required=false")
        try:
            if self.data_type.clap_macros:
                macros.update(self.data_type.clap_macros)
            # i.e. CLI groups are managed through the code dynamically
            macros.update(self.additional_clap_macros)
        except Exception as ex:
            logging.exception("Error getting clap_macros for %s: %s", self, ex)
        return f"#[arg({', '.join(sorted(macros))})]"


class StructInput(common_rust.Struct):
    field_type_class_: Type[common_rust.StructField] = StructInputField
    clap_macros: set[str] = set()
    original_data_type: BaseCompoundType | BaseCompoundType | None = None
    is_group: bool = False
    is_required: bool = False


class EnumGroupStructInputField(StructInputField):
    """Container for complex Enum field"""

    sdk_parent_enum_variant: str | None = None


class EnumGroupStruct(common_rust.Struct):
    """Container for complex Enum containing Array"""

    field_type_class_: Type[
        common_rust.StructField
    ] = EnumGroupStructInputField
    base_type: str = "struct"
    sdk_enum_name: str
    is_group: bool = True
    is_required: bool = False


class StructFieldResponse(common_rust.StructField):
    """Response Structure Field"""

    @property
    def type_hint(self):
        typ_hint = self.data_type.type_hint
        if self.is_optional and not typ_hint.startswith("Option<"):
            typ_hint = f"Option<{typ_hint}>"
        return typ_hint

    @property
    def serde_macros(self):
        macros = set([])
        if self.local_name != self.remote_name:
            macros.add(f'rename="{self.remote_name}"')
        return f"#[serde({', '.join(sorted(macros))})]"

    def get_structable_macros(
        self, struct: "StructResponse", service_name: str, resource_name: str
    ):
        macros = set([])
        if self.is_optional:
            macros.add("optional")
        if self.local_name != self.remote_name:
            macros.add(f'title="{self.remote_name}"')
        # Fully Qualified Attribute Name
        fqan: str = ".".join(
            [service_name, resource_name, self.remote_name]
        ).lower()
        # Check the known alias of the field by FQAN
        alias = common.FQAN_ALIAS_MAP.get(fqan)
        if (
            "id" in struct.fields.keys()
            and not (self.local_name in BASIC_FIELDS or alias in BASIC_FIELDS)
        ) or (
            "id" not in struct.fields.keys()
            and (self.local_name not in list(struct.fields.keys())[-10:])
        ):
            # Only add "wide" flag if field is not in the basic fields AND
            # there is at least "id" field existing in the struct OR the
            # field is not in the first 10
            macros.add("wide")
        return f"#[structable({', '.join(sorted(macros))})]"


class StructResponse(common_rust.Struct):
    field_type_class_: Type[common_rust.StructField] = StructFieldResponse


class TupleStruct(common_rust.Struct):
    """Rust tuple struct without named fields"""

    base_type: str = "struct"
    tuple_fields: list[common_rust.StructField] = []

    @property
    def imports(self):
        imports: set[str] = set([])
        for field in self.tuple_fields:
            imports.update(field.data_type.imports)
        return imports


class DictionaryInput(common_rust.Dictionary):
    lifetimes: set[str] = set()
    original_data_type: BaseCompoundType | BaseCompoundType | None = None

    @property
    def type_hint(self):
        return f"Vec<(String, {self.value_type.type_hint})>"

    @property
    def imports(self):
        imports = set(["crate::common::parse_key_val"])
        imports.update(self.value_type.imports)
        return imports

    @property
    def clap_macros(self):
        return set(
            [
                "long",
                'value_name="key=value"',
                f"value_parser=parse_key_val::<String, {self.value_type.type_hint}>",
            ]
        )


class StringEnum(common_rust.StringEnum):
    imports: set[str] = set(["clap::ValueEnum"])


class ArrayInput(common_rust.Array):
    original_data_type: common_rust.BaseCompoundType | common_rust.BaseCombinedType | common_rust.BasePrimitiveType | None = (
        None
    )

    @property
    def clap_macros(self):
        macros: set[str] = set(["long", "action=clap::ArgAction::Append"])
        macros.update(self.item_type.clap_macros)
        return macros


class ArrayResponse(common_rust.Array):
    """Vector of data for the Reponse

    in the reponse need to be converted to own type to implement Display"""

    @property
    def type_hint(self):
        return f"Vec{self.item_type.type_hint}"


class HashMapResponse(common_rust.Dictionary):
    lifetimes: set[str] = set()

    @property
    def type_hint(self):
        return f"HashMapString{self.value_type.type_hint}"

    @property
    def imports(self):
        imports = self.value_type.imports
        imports.add("std::collections::HashMap")
        return imports


class CommaSeparatedList(common_rust.CommaSeparatedList):
    @property
    def type_hint(self):
        return f"Vec<{self.item_type.type_hint}>"


class RequestParameter(common_rust.RequestParameter):
    """OpenAPI request parameter in the Rust SDK form"""

    @property
    def clap_macros(self):
        macros: set[str] = set()
        if not self.is_required:
            macros.add("long")
        return f"#[arg({', '.join(macros)})]"


class RequestTypeManager(common_rust.TypeManager):
    primitive_type_mapping: dict[
        Type[model.PrimitiveType], Type[BasePrimitiveType]
    ] = {
        model.PrimitiveString: String,
        model.ConstraintString: String,
        model.PrimitiveAny: JsonValue,
    }

    data_type_mapping: dict[
        Type[model.ADT], Type[BaseCombinedType] | Type[BaseCompoundType]
    ]

    data_type_mapping = {
        model.Struct: StructInput,
        model.Dictionary: DictionaryInput,
        model.Array: ArrayInput,
        model.CommaSeparatedList: ArrayInput,
        model.Set: ArrayInput,
    }

    request_parameter_class: Type[
        common_rust.RequestParameter
    ] = RequestParameter
    string_enum_class = StringEnum

    def get_local_attribute_name(self, name: str) -> str:
        """Get localized attribute name"""
        attr_name = "_".join(
            x.lower() for x in re.split(common.SPLIT_NAME_RE, name)
        )
        if attr_name == "type":
            attr_name = "_type"
        return attr_name

    def get_remote_attribute_name(self, name: str) -> str:
        """Get the attribute name on the SDK side"""
        return self.get_local_attribute_name(name)

    def get_var_name_for(self, obj) -> str:
        attr_name = "_".join(
            x.lower() for x in re.split(common.SPLIT_NAME_RE, obj.name)
        )
        if attr_name == "type":
            attr_name = "_type"
        return attr_name

    def _get_one_of_type(
        self, type_model: model.OneOfType
    ) -> BaseCompoundType | BaseCombinedType | BasePrimitiveType:
        """Convert `model.OneOfType` into Rust model"""
        result = super()._get_one_of_type(type_model)

        # Field is of Enum type.
        if isinstance(result, common_rust.Enum):
            variant_classes = [
                x.data_type.__class__ for x in result.kinds.values()
            ]

            if (
                StringEnum in variant_classes
                and ArrayInput in variant_classes
                and len(variant_classes) == 2
            ):
                # There is a StringEnum and Array in the Enum. Clap cannot
                # handle it so we convert StringEnum variants into flags
                # and keep only rest
                # This usecase is here at least to handle server.networks
                # which are during creation `none`|`auto`|`JSON`
                # On the SDK side where this method is not overriden there
                # would be a naming conflict resulting in `set_models` call
                # adding type name as a suffix.
                sdk_enum_name = result.name + result.__class__.__name__
                obj = EnumGroupStruct(
                    name=self.get_model_name(type_model.reference),
                    kinds={},
                    sdk_enum_name=sdk_enum_name,
                )
                field_class = obj.field_type_class_
                if not type_model.reference:
                    raise NotImplementedError
                name = type_model.reference.name
                for k, v in result.kinds.items():
                    if isinstance(v.data_type, common_rust.StringEnum):
                        for x in v.data_type.variants:
                            field = field_class(
                                local_name=f"{x.lower()}_{name}",
                                remote_name=f"{v.data_type.name}::{x}",
                                sdk_parent_enum_variant=f"{sdk_enum_name}::{k}",
                                data_type=BooleanFlag(),
                                is_optional=False,
                                is_nullable=False,
                            )
                            obj.fields[field.local_name] = field
                    else:
                        field = field_class(
                            local_name=f"{name}",
                            remote_name=f"{sdk_enum_name}::{k}",
                            data_type=v.data_type,
                            is_optional=True,
                            is_nullable=False,
                        )
                        obj.fields[field.local_name] = field
                result = obj

        return result

    def convert_model(
        self,
        type_model: model.PrimitiveType | model.ADT | model.Reference,
    ) -> BasePrimitiveType | BaseCombinedType | BaseCompoundType:
        """Get local destination type from the ModelType"""
        model_ref: model.Reference | None = None
        typ: BasePrimitiveType | BaseCombinedType | BaseCompoundType | None = (
            None
        )
        if isinstance(type_model, model.Reference):
            model_ref = type_model
            type_model = self._get_adt_by_reference(model_ref)
        elif isinstance(type_model, model.ADT):
            # Direct composite type
            model_ref = type_model.reference

        # CLI hacks
        if isinstance(type_model, model.Array):
            if isinstance(type_model.item_type, model.Reference):
                item_type = self._get_adt_by_reference(type_model.item_type)
            else:
                item_type = type_model.item_type

            if (
                isinstance(item_type, model.Struct)
                and len(item_type.fields.keys()) > 1
            ):
                # An array of structs with more then 1 field
                # Array of Structs can not be handled by the CLI (input).
                # Therefore handle underlaying structure as Json saving
                # reference to the original "expected" stuff to make final
                # input conversion possible
                original_data_type = self.convert_model(item_type)
                # We are not interested to see unused data in the submodels
                if not item_type.reference:
                    raise NotImplementedError
                self.refs.pop(item_type.reference, None)
                typ = self.data_type_mapping[model.Array](
                    description=common_rust.sanitize_rust_docstrings(
                        type_model.description
                    ),
                    original_data_type=original_data_type,
                    item_type=JsonValue(),
                )

        if typ:
            if model_ref:
                self.refs[model_ref] = typ
        else:
            # Not hacked anything, invoke superior method
            typ = super().convert_model(type_model)
        return typ

    def _get_struct_type(self, type_model: model.Struct) -> common_rust.Struct:
        """Convert model.Struct into rust_cli `Struct`"""
        struct_class = self.data_type_mapping[model.Struct]
        mod = struct_class(
            name=self.get_model_name(type_model.reference),
            description=common_rust.sanitize_rust_docstrings(
                type_model.description
            ),
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
                if isinstance(
                    field_data_type.item_type,
                    (common_rust.Array, DictionaryInput, String),
                ):
                    # Unwrap Option<Option<...>>
                    field_data_type = field_data_type.item_type
            elif isinstance(field_data_type, EnumGroupStruct):
                field_data_type.is_required = field.is_required
            f = field_class(
                local_name=self.get_local_attribute_name(field_name),
                remote_name=self.get_remote_attribute_name(field_name),
                description=common_rust.sanitize_rust_docstrings(
                    field.description
                ),
                data_type=field_data_type,
                is_optional=not field.is_required,
                is_nullable=is_nullable,
            )
            if mod.name != "Request" and isinstance(
                field_data_type, struct_class
            ):
                print(f"Struct name = {mod.name}")
                field_data_type.is_group = True
                field_data_type.is_required = field.is_required
            if isinstance(field_data_type, self.option_type_class):
                f.is_nullable = True
            mod.fields[field_name] = f

        return mod

    def _get_array_type(self, type_model: model.Array) -> common_rust.Array:
        """Convert `model.Array` into corresponding Rust model"""
        item_type = self.convert_model(type_model.item_type)
        struct_class = self.data_type_mapping[model.Struct]
        item_ref: model.Reference | None = None
        if isinstance(type_model.item_type, model.Reference):
            item_ref = type_model.item_type
        elif hasattr(type_model.item_type, "reference"):
            item_ref = type_model.item_type.reference
        if isinstance(item_type, struct_class):
            if len(item_type.fields.keys()) == 1:
                # Server.security_groups is an object with only name -> simplify
                # Only simplify structure with single simple property and name !=
                # "Request" (root request)
                only_field_name = list(item_type.fields.keys())[0]
                only_field = item_type.fields[only_field_name]
                if not isinstance(only_field.data_type, StructInput):
                    # If there is only single field in the struct and it is not a
                    # new struct simplify it.
                    simplified_data_type = only_field.data_type.model_copy()
                    simplified_data_type.original_data_type = item_type
                    logging.debug(
                        "Replacing single field object %s with %s",
                        type_model.item_type,
                        simplified_data_type,
                    )
                    if item_ref:
                        self.refs.pop(item_ref)
                    item_type = simplified_data_type
        elif isinstance(item_type, DictionaryInput):
            # Array of Freestyle objects in CLI can be only represented as
            # array of JsonValue
            simplified_data_type = JsonValue()
            simplified_data_type.original_data_type = item_type
            if item_ref:
                self.refs.pop(item_ref)
            item_type = simplified_data_type

        return self.data_type_mapping[model.Array](
            name=self.get_model_name(type_model.reference), item_type=item_type
        )


class ResponseTypeManager(common_rust.TypeManager):
    primitive_type_mapping: dict[
        Type[model.PrimitiveType], Type[BasePrimitiveType]
    ] = {
        model.PrimitiveString: String,
        model.ConstraintString: String,
    }

    data_type_mapping = {
        model.Struct: StructResponse,
        model.Array: ArrayResponse,
        model.Dictionary: HashMapResponse,
    }

    def get_model_name(self, model_ref: model.Reference | None) -> str:
        """Get the localized model type name

        In order to avoid collision between structures in request and
        response we prefix all types with `Response`
        :returns str: Type name
        """
        if not model_ref:
            return "Response"
        return "Response" + "".join(
            x.capitalize()
            for x in re.split(common.SPLIT_NAME_RE, model_ref.name)
        )

    def convert_model(
        self,
        type_model: model.PrimitiveType | model.ADT | model.Reference,
    ) -> BasePrimitiveType | BaseCombinedType | BaseCompoundType:
        """Get local destination type from the ModelType"""
        model_ref: model.Reference | None = None
        typ: BasePrimitiveType | BaseCombinedType | BaseCompoundType | None = (
            None
        )
        if isinstance(type_model, model.Reference):
            model_ref = type_model
            type_model = self._get_adt_by_reference(model_ref)
        elif isinstance(type_model, model.ADT):
            # Direct composite type
            model_ref = type_model.reference

        # CLI response PRE hacks
        if isinstance(type_model, model.Array):
            if isinstance(type_model.item_type, String):
                # Array of string is replaced by `VecString` type
                typ = VecString()
            elif (
                model_ref
                and model_ref.name == "links"
                and model_ref.type == model.Array
            ):
                # Array of "links" is replaced by Json Value
                typ = common_rust.JsonValue()

        if typ:
            if model_ref:
                self.refs[model_ref] = typ
        else:
            # Not hacked anything, invoke superior method
            typ = super().convert_model(type_model)

        # POST hacks
        if typ and isinstance(typ, common_rust.StringEnum):
            # There is no sense of Enum in the output. Convert to the plain
            # string
            typ = String(
                description=common_rust.sanitize_rust_docstrings(
                    typ.description
                )
            )
        return typ

    def _simplify_oneof_combinations(self, type_model, kinds):
        """Simplify certain known oneOf combinations"""
        kinds_classes = [x["class"] for x in kinds]
        if String in kinds_classes and common_rust.Number in kinds_classes:
            # oneOf [string, number] => NumString
            kinds.clear()
            kinds.append({"local": NumString(), "class": NumString})
        elif String in kinds_classes and common_rust.Integer in kinds_classes:
            # oneOf [string, integer] => NumString
            kinds.clear()
            kinds.append({"local": IntString(), "class": IntString})
        elif String in kinds_classes and common_rust.Boolean in kinds_classes:
            # oneOf [string, boolean] => String
            kinds.clear()
            kinds.append({"local": BoolString(), "class": BoolString})
        super()._simplify_oneof_combinations(type_model, kinds)

    def get_subtypes(self):
        """Get all subtypes excluding TLA"""
        emited_data: set[str] = set()
        for k, v in self.refs.items():
            if (
                k
                and isinstance(
                    v,
                    (
                        common_rust.Enum,
                        common_rust.Struct,
                        common_rust.StringEnum,
                        common_rust.Dictionary,
                        common_rust.Array,
                    ),
                )
                and k.name != "Body"
            ):
                key = v.base_type + v.type_hint
                if key not in emited_data:
                    emited_data.add(key)
                    yield v


class RustCliGenerator(BaseGenerator):
    def __init__(self):
        super().__init__()

    def _format_code(self, *args):
        """Format code using Rustfmt

        :param *args: Path to the code to format
        """
        for path in args:
            subprocess.run(["rustfmt", "--edition", "2021", path])

    def get_parser(self, parser):
        parser.add_argument(
            "--operation-type",
            choices=[
                "list",
                "show",
                "create",
                "set",
                "action",
                "delete",
                "download",
                "upload",
                "json",
            ],
            help="Rust CLI Command type (only for rust-cli target)",
        )
        parser.add_argument(
            "--command-name",
            help="Rust CLI Command name (used as final module name)",
        )
        parser.add_argument(
            "--cli-mod-path",
            help="Mod path (dot separated) of the corresponding SDK command (when non standard)",
        )

        parser.add_argument(
            "--sdk-mod-path",
            help="Mod path (dot separated) of the corresponding SDK command (when non standard)",
        )

        return parser

    def _render_command(
        self,
        context: dict,
        impl_template: str,
        impl_dest: Path,
    ):
        """Render command code"""
        self._render(impl_template, context, impl_dest.parent, impl_dest.name)

    def generate(
        self, res, target_dir, openapi_spec=None, operation_id=None, args=None
    ):
        """Generate code for the Rust openstack_cli"""
        logging.debug(
            "Generating Rust CLI code for `%s` in %s"
            % (operation_id, target_dir)
        )
        work_dir = Path(target_dir, "rust", "openstack_cli", "src")

        if not openapi_spec:
            openapi_spec = common.get_openapi_spec(args.openapi_yaml_spec)
        if not operation_id:
            operation_id = args.openapi_operation_id

        (path, method, spec) = common.find_openapi_operation(
            openapi_spec, operation_id
        )
        _, res_name = res.split(".") if res else (None, None)
        resource_name = common.get_resource_names_from_url(path)[-1]

        openapi_parser = model.OpenAPISchemaParser()
        operation_params: list[model.RequestParameter] = []
        sdk_mod_path_base = common.get_rust_sdk_mod_path(
            args.service_type,
            args.api_version,
            args.module_path or path,
        )
        cli_mod_path = common.get_rust_cli_mod_path(
            args.service_type,
            args.api_version,
            args.module_path or path,
        )
        target_class_name = resource_name

        # Collect all operation parameters
        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            if (
                ("{" + param["name"] + "}") in path and param["in"] == "path"
            ) or param["in"] != "path":
                # Respect path params that appear in path and not path params
                param_ = openapi_parser.parse_parameter(param)
                if param_.name == f"{res_name}_id":
                    # for i.e. routers/{router_id} we want local_name to be `id` and not `router_id`
                    param_.name = "id"
                operation_params.append(param_)

        # List of operation variants (based on the body)
        operation_variants = common_rust.get_operation_variants(
            spec, args.operation_name
        )

        body_types: list[str] = []
        if args.operation_type == "upload":
            # collect registered media types for upload operation
            request_body = spec.get("requestBody")
            content = request_body.get("content", {})
            body_types = list(content.keys())

        for operation_variant in operation_variants:
            logging.debug("Processing variant %s" % operation_variant)
            additional_imports = set()
            type_manager: common_rust.TypeManager = RequestTypeManager()
            response_type_manager: common_rust.TypeManager = (
                ResponseTypeManager()
            )
            result_is_list: bool = False
            if operation_params:
                type_manager.set_parameters(operation_params)

            mod_name = "_".join(
                x.lower()
                for x in re.split(
                    common.SPLIT_NAME_RE,
                    (
                        args.module_name
                        or args.operation_name
                        or args.operation_type
                        or method
                    ),
                )
            )

            operation_body = operation_variant.get("body")
            microversion: str | None = None
            mod_suffix: str = ""
            if operation_body:
                min_ver = operation_body.get("x-openstack", {}).get("min-ver")
                if min_ver:
                    mod_suffix = "_" + min_ver.replace(".", "")
                    microversion = min_ver

                (_, all_types) = openapi_parser.parse(operation_body)

                # Certain hacks
                for parsed_type in list(all_types):
                    # iterate over listed all_types since we want to modify list
                    if resource_name == "server" and method.lower() == "post":
                        # server declares OS-SCH-HNT:scheduler_hints as
                        # "alias" for normal scheduler hints, but the whole
                        # struct is there. For the cli it makes no sense and
                        # we filter it out from the parsed data
                        object_to_remove = "OS-SCH-HNT:scheduler_hints"
                        if parsed_type.reference == model.Reference(
                            name=object_to_remove, type=model.Struct
                        ):
                            all_types.remove(parsed_type)
                        elif parsed_type.reference is None and isinstance(
                            parsed_type, model.Struct
                        ):
                            parsed_type.fields.pop(object_to_remove, None)

                # and feed them into the TypeManager
                type_manager.set_models(all_types)

            sdk_mod_path: list[str] = sdk_mod_path_base.copy()
            sdk_mod_path.append((args.sdk_mod_name or mod_name) + mod_suffix)
            mod_name += mod_suffix

            result_def: dict = {}
            response_def: dict | None = {}
            resource_header_metadata: dict = {}

            # Process response information
            # # Prepare information about response
            if method.upper() != "HEAD":
                response_def = None
                for code, rspec in spec["responses"].items():
                    if not code.startswith("2"):
                        continue
                    content = rspec.get("content", {})
                    if "application/json" in content:
                        response_spec = content["application/json"]
                        oneof = response_spec["schema"].get("oneOf")
                        discriminator = (
                            response_spec["schema"]
                            .get("x-openstack", {})
                            .get("discriminator")
                        )
                        if oneof:
                            if not discriminator:
                                # Server returns server or reservation info. For the cli it is not very helpful and we look for response candidate with the resource_name in the response
                                for candidate in oneof:
                                    if (
                                        args.operation_type == "action"
                                        and candidate.get(
                                            "x-openstack", {}
                                        ).get("action-name")
                                        == args.operation_name
                                    ):
                                        response_def = candidate
                                    elif (
                                        resource_name
                                        and candidate.get("type") == "object"
                                        and resource_name
                                        in candidate.get("properties", {})
                                    ):
                                        # Actually for the sake of the CLI it may make sense to merge all candidates
                                        response_def = candidate["properties"][
                                            resource_name
                                        ]
                            else:
                                raise NotImplementedError
                        else:
                            response_def, _ = common.find_resource_schema(
                                response_spec["schema"],
                                None,
                                args.response_key or resource_name,
                            )
                        if not response_def:
                            continue

                        if response_def["type"] == "object":
                            (_, response_all_types) = openapi_parser.parse(
                                response_def
                            )
                            response_type_manager.set_models(
                                response_all_types
                            )
                        elif response_def["type"] == "string":
                            (root_dt, _) = openapi_parser.parse(response_def)
                            if not root_dt:
                                raise RuntimeError(
                                    "Response data can not be processed"
                                )
                            field = common_rust.StructField(
                                local_name="dummy",
                                remote_name="dummy",
                                data_type=response_type_manager.convert_model(
                                    root_dt
                                ),
                                is_optional=False,
                            )
                            tuple_struct = TupleStruct(name="Response")
                            tuple_struct.tuple_fields.append(field)
                            response_type_manager.refs[
                                model.Reference(name="Body", type=TupleStruct)
                            ] = tuple_struct
                        response_props = response_spec["schema"].get(
                            "properties", {}
                        )
                        if (
                            response_props
                            and response_props[
                                list(response_props.keys())[0]
                            ].get("type")
                            == "array"
                        ):
                            result_is_list = True

                additional_imports.add(
                    "openstack_sdk::api::" + "::".join(sdk_mod_path)
                )
                root_type = response_type_manager.get_root_data_type()
                if args.operation_type == "list":
                    # Make plural form for listing
                    target_class_name = common.get_plural_form(
                        target_class_name
                    )
                    additional_imports.update(
                        ["openstack_sdk::api::{paged, Pagination}"]
                    )
                if args.operation_type == "download":
                    additional_imports.add("crate::common::download_file")
                if args.operation_type == "upload":
                    additional_imports.add(
                        "crate::common::build_upload_asyncread"
                    )
                if (
                    isinstance(root_type, StructResponse)
                    and root_type.fields
                    or isinstance(root_type, TupleStruct)
                    and root_type.tuple_fields
                ):
                    additional_imports.add("openstack_sdk::api::QueryAsync")
                else:
                    additional_imports.add("openstack_sdk::api::RawQueryAsync")

                if resource_header_metadata:
                    additional_imports.add(
                        "crate::common::HashMapStringString"
                    )
                    additional_imports.add("std::collections::HashMap")
                    if (
                        len(
                            [
                                x
                                for x in resource_header_metadata.keys()
                                if "*" in x
                            ]
                        )
                        > 0
                    ):
                        additional_imports.add("regex::Regex")

                additional_imports.update(type_manager.get_imports())
                additional_imports.update(response_type_manager.get_imports())
                # Deserialize is already in template since it is uncoditionally required
                additional_imports.discard("serde::Deserialize")
                if args.find_implemented_by_sdk:
                    additional_imports.add("openstack_sdk::api::find")
                    additional_imports.add(
                        "::".join(
                            [
                                "openstack_sdk::api",
                                "::".join(sdk_mod_path[:-1]),
                                "find",
                            ]
                        )
                    )

                context = dict(
                    operation_id=operation_id,
                    operation_type=args.operation_type,
                    command_description=common_rust.sanitize_rust_docstrings(
                        spec.get("description")
                    ),
                    type_manager=type_manager,
                    resource_name=resource_name,
                    response_type_manager=response_type_manager,
                    target_class_name="".join(
                        x.title() for x in target_class_name.split("_")
                    ),
                    sdk_struct_name="Request",
                    sdk_service_name=common.get_rust_service_type_from_str(
                        args.service_type
                    ),
                    service_type=args.service_type,
                    url=path[1:] if path.startswith("/") else path,
                    method=method,
                    resource_key=None,
                    resource_header_metadata=resource_header_metadata,
                    sdk_mod_path=sdk_mod_path,
                    cli_mod_path=cli_mod_path,
                    result_def=result_def,
                    last_path_parameter=None,
                    body_types=body_types,
                    additional_imports=additional_imports,
                    find_present=args.find_implemented_by_sdk,
                    microversion=microversion,
                    result_is_list=result_is_list,
                )

                if not args.cli_mod_path:
                    # mod_name = args.operation_name or args.operation_type.value
                    impl_path = Path(
                        work_dir, "/".join(cli_mod_path), f"{mod_name}.rs"
                    )

                self._render_command(
                    context,
                    "rust_cli/impl.rs.j2",
                    impl_path,
                )

                self._format_code(impl_path)

                yield (cli_mod_path, mod_name, path)
