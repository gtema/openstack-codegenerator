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
import copy
import logging
from pathlib import Path
import re
import subprocess

from pydantic import BaseModel

from codegenerator.base import BaseGenerator
from codegenerator import common
from codegenerator import types
from codegenerator import model

# from generator.common.schema import RestEndpointSchema

OPENAPI_RUST_TYPE_MAPPING = {
    "string": {"default": "Cow<'a, str>"},
    "integer": {"default": "u32", "int32": "u32", "int64": "u64"},
    "number": {"default": "f32", "float": "f32", "double": "f64"},
    "boolean": {"default": "bool"},
}


class BasePrimitiveType(BaseModel):
    lifetimes: str | None = None
    imports: set[str] = set()
    builder_macros: set[str] = set([])


class BaseCombinedType(BaseModel):
    """A Container Type (Array, Option)"""

    pass


class BaseCompoundType(BaseModel):
    """A Complex Type (Enum/Struct)"""

    name: str
    base_type: str
    description: str | None = None
    macros: list[str] = []


class String(BasePrimitiveType):
    lifetimes: str = set(["'a"])
    imports: set[str] = set(["std::borrow::Cow"])
    builder_macros: set[str] = set(["setter(into)"])

    @property
    def type_hint(self):
        return "Cow<'a, str>"


class Boolean(BasePrimitiveType):
    @property
    def type_hint(self):
        return "bool"


class Number(BasePrimitiveType):
    format: str | None = None

    @property
    def type_hint(self):
        if self.format == "float":
            return "f32"
        elif self.format == "double":
            return "f64"
        else:
            return "f32"


class Integer(BasePrimitiveType):
    format: str | None = None

    @property
    def type_hint(self):
        if self.format == "int32":
            return "i32"
        elif self.format == "int64":
            return "i64"
        return "i32"


class Null(BasePrimitiveType):
    @property
    def type_hint(self):
        return "None::<String>"


class JsonValue(BasePrimitiveType):
    imports: set[str] = set(["serde_json::Value"])
    builder_macros: set[str] = set(["setter(into)"])

    @property
    def type_hint(self):
        return "Value"


class EnumKind(BaseModel):
    name: str
    description: str | None = None
    data_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType

    @property
    def type_hint(self):
        if isinstance(self.data_type, Struct):
            return self.data_type.name
        else:
            return self.data_type.type_hint


class Enum(BaseCompoundType):
    base_type: str = "enum"
    kinds: dict[str, EnumKind]

    @property
    def lifetimes(self):
        lifetimes_ = set()
        for kind in self.kinds.values():
            if kind.data_type.lifetimes:
                lifetimes_.update(kind.data_type.lifetimes)
        return lifetimes_

    @property
    def type_hint(self):
        return self.name

    @property
    def imports(self):
        imports = set()
        for kind in self.kinds.values():
            imports.update(kind.data_type.imports)
        return imports

    @property
    def builder_macros(self):
        macros = set(["setter(into)"])
        return macros


class StructField(BaseModel):
    local_name: str
    description: str | None = None
    data_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType
    is_optional: bool = True
    is_nullable: bool = False
    # macros: set(str) = set()

    @property
    def type_hint(self):
        # return self.data_type
        typ_hint = self.data_type.type_hint
        if self.is_optional:
            typ_hint = f"Option<{typ_hint}>"
        return typ_hint

    @property
    def builder_macros(self):
        macros = set(["default"])
        macros.update(self.data_type.builder_macros)
        # if isinstance(self.data_type, BaseCompoundType):
        #    macros.add("private")
        return f"[builder({', '.join(macros)})]"


class Struct(BaseCompoundType):
    base_type: str = "struct"
    fields: dict[str, StructField] = {}

    @property
    def lifetimes(self):
        lifetimes_ = set()
        for field in self.fields.values():
            if field.data_type.lifetimes and (
                isinstance(field.data_type, BasePrimitiveType)
                or isinstance(field.data_type, BaseCombinedType)
            ):
                lifetimes_.update(field.data_type.lifetimes)
        return lifetimes_

    @property
    def type_hint(self):
        return self.name

    @property
    def imports(self):
        imports = set()
        for field in self.fields.values():
            imports.update(field.data_type.imports)
        return imports

    @property
    def builder_macros(self):
        macros = set(["setter(into)"])
        return macros


class Dictionary(BaseCombinedType):
    value_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType

    @property
    def type_hint(self):
        return f"BTreeMap<Cow<'a, str>, {self.value_type.type_hint}>"

    @property
    def imports(self):
        imports = set(["std::collections::BTreeMap"])
        imports.update(self.value_type.imports)
        return imports

    @property
    def lifetimes(self):
        lt = set(["'a"])
        if self.value_type.lifetimes:
            lt.update(self.value_type.lifetimes)
        return lt

    @property
    def builder_macros(self):
        macros = set(["setter(into)"])
        return macros


class Array(BaseCombinedType):
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


class Option(BaseCombinedType):
    base_type: str = "Option"
    item_type: BasePrimitiveType | BaseCombinedType | BaseCompoundType

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
        return macros


data_type_mapping = {
    model.PrimitiveString: String,
    model.ConstraintString: String,
    model.PrimitiveNumber: Number,
    model.ConstraintNumber: Number,
    model.ConstraintInteger: Integer,
    model.PrimitiveBoolean: Boolean,
    model.PrimitiveNull: Null,
    model.PrimitiveAny: JsonValue,
}


def get_type(data_type):
    typ = data_type_mapping.get(data_type.__class__)
    if not typ:
        raise RuntimeError("No mapping for %s" % data_type)
    # if isinstance(data_type, model.Array):
    #    if len(self.kinds) == 2:
    #        typs = [x.__class__ for x in self.kinds]
    #        if model.PrimitiveNull in typs:
    #            # a) Type + Null -> Option
    #            typ = [x for x in typs if x is not model.PrimitiveNull][0]
    #            return f"Option<{get_type(typ).type_hint}>"
    #        elif model.Array in typs:
    #            list_type = [x for x in typs if x is model.Array][0]
    #            item_type = [x for x in typs if x is not model.Array][0]

    return typ(**data_type.model_dump())


class TypeManager:
    models: list = []
    refs: dict = {}

    def get_local_attribute_name(self, name):
        return "_".join(x.lower() for x in re.split(r":|_|-", name))

    def get_model_name(self, model_ref):
        if not model_ref:
            return "Root"
        return "".join(x.title() for x in re.split(r":|_|-", model_ref.name))

    def _get_adt_by_reference(self, model_ref):
        for model_ in self.models:
            if model_.reference == model_ref:
                return model_
        raise RuntimeError("Cannot find reference %s" % model_ref)

    def get_dst_type(
        self, type_model: model.PrimitiveType | model.ADT | model.Reference
    ):
        logging.debug("Get RustSDK type for %s", type_model)
        model_ref = None
        if isinstance(type_model, model.Reference):
            model_ref = type_model
            type_model = self._get_adt_by_reference(type_model)
        elif isinstance(type_model, model.ADT):
            # Direct composite type
            model_ref = type_model.reference
        else:
            # Primitive
            typ = data_type_mapping.get(type_model.__class__)
            if not typ:
                raise RuntimeError("No mapping for %s" % type_model)
            logging.debug("Returning %s for %s", typ, type_model.__class__)
            return typ(**type_model.model_dump())

        # Composite type
        if model_ref and model_ref in self.refs:
            return self.refs[model_ref]
        if isinstance(type_model, model.Array):
            typ = self.get_array_type(type_model)
        elif isinstance(type_model, model.Struct):
            typ = self.get_struct_type(type_model)
        elif isinstance(type_model, model.OneOfType):
            typ = self.get_one_of_type(type_model)
        elif isinstance(type_model, model.Dictionary):
            typ = Dictionary(
                value_type=self.get_dst_type(type_model.value_type)
            )

        self.refs[model_ref] = typ
        return typ

    def get_array_type(self, type_model):
        return Array(
            name=self.get_model_name(type_model.reference),
            item_type=self.get_dst_type(type_model.item_type),
        )

    def get_one_of_type(self, type_model):
        kinds: list[dict] = []
        is_nullable: bool = False
        result_data_type = None
        for kind in type_model.kinds:
            if isinstance(kind, model.PrimitiveNull):
                # Remove null from candidates and instead wrap with Option
                is_nullable = True
                continue
            kind_type = self.get_dst_type(kind)
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
        kinds_classes = [x["class"] for x in kinds]
        if String in kinds_classes and Number in kinds_classes:
            # oneOf [string, number] => number
            for typ in list(kinds):
                if typ["class"] == String:
                    kinds.remove(typ)
        elif String in kinds_classes and Integer in kinds_classes:
            # oneOf [string, integer] => integer
            for typ in list(kinds):
                if typ["class"] == String:
                    kinds.remove(typ)
        elif String in kinds_classes and Boolean in kinds_classes:
            # oneOf [string, boolean] => boolean
            for typ in list(kinds):
                if typ["class"] == String:
                    kinds.remove(typ)

        if len(kinds) == 2:
            list_type = [x["local"] for x in kinds if x["class"] == Array]
            if list_type:
                # Typ + list[Typ] => Vec<Typ>
                list_type = list_type[0]
                item_type = [x["local"] for x in kinds if x["class"] != Array][
                    0
                ]
                if item_type.__class__ == list_type.item_type.__class__:
                    result_data_type = Array(item_type=item_type)
        elif len(kinds) == 1:
            result_data_type = kinds[0]["local"]

        if not result_data_type:
            result_data_type = Enum(
                name=self.get_model_name(type_model.reference), kinds={}
            )
            cnt = 0
            for kind in kinds:
                cnt += 1
                kind_data_type = kind["local"]
                kind_description: str | None = None
                if isinstance(kind["model"], model.ADT):
                    kind_name = self.get_model_name(kind["model"])
                    kind_description = kind["model"].description
                else:
                    kind_name = f"F{cnt}"
                enum_kind = EnumKind(
                    name=kind_name,
                    description=kind_description,
                    data_type=kind_data_type,
                )
                result_data_type.kinds[enum_kind.name] = enum_kind

        if is_nullable:
            result_data_type = Option(item_type=result_data_type)

        return result_data_type

    def get_struct_type(self, type_model):
        mod = Struct(
            name=self.get_model_name(type_model.reference),
            description=type_model.description,
        )
        for field_name, field in type_model.fields.items():
            is_nullable: bool = False
            field_data_type = self.get_dst_type(field.data_type)
            if isinstance(field_data_type, Option):
                # Unwrap Option into "is_nullable"
                # NOTE: but perhaps Option<Option> is
                # better (not set vs set explicitly to
                # None )
                is_nullable = True
                field_data_type = field_data_type.item_type
            f = StructField(
                local_name=self.get_local_attribute_name(field_name),
                description=field.description,
                data_type=field_data_type,
                is_optional=not field.is_required,
                is_nullable=is_nullable,
            )
            if isinstance(field_data_type, Option):
                f.is_nullable = True
            mod.fields[field_name] = f
        return mod

    def set_models(self, models):
        """Process (translate) ADT models into Rust SDK style"""
        self.models = models
        unique_model_names: set[str] = set()
        for model_ in models:
            model_data_type = self.get_dst_type(model_)
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
                and (isinstance(v, Enum) or isinstance(v, Struct))
                and v.name != "Root"
            ):
                yield v

    def get_root_data_type(self):
        """Get TLA type"""
        for k, v in self.refs.items():
            if not k:
                return v

    def get_imports(self):
        imports = set()
        for item in self.refs.values():
            imports.update(item.imports)
        return imports

    def get_subtype_derive_macros(self, subtype):
        return "[derive(Debug, Deserialize, Clone, Serialize)]"

    def get_subtype_field_serde_macros(self, field):
        macros = set()
        if not field.is_nullable:
            macros.add('skip_serializing_if="Option::is_none"')
        if macros:
            return f"#[serde({', '.join(macros)})]"
        return ""


class RustSdkGenerator(BaseGenerator):
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
            "--response-key",
            help="Rust SDK response key (only required when normal detection does not work)",
        )

        parser.add_argument(
            "--response-list-item-key",
            help='Rust SDK list response item key (specifies whether list items are wrapped in additional container `{"keypairs":["keypair":{}]}`)',
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
        """Generate code for the Rust openstack_sdk"""
        logging.debug(
            "Generating Rust SDK code for %s in %s"
            % (operation_id, target_dir)
        )

        if not openapi_spec:
            openapi_spec = common.get_openapi_spec(args.openapi_yaml_spec)
        if not operation_id:
            operation_id = args.openapi_operation_id
        (path, method, spec) = common.find_openapi_operation(
            openapi_spec, operation_id
        )
        srv_name, res_name = res.split(".") if res else (None, None)
        path_resources = common.get_resource_names_from_url(path)
        res_name = path_resources[-1]
        if path.endswith("action"):
            logging.warn("Skipping action for now")
            return

        global_params = {}
        global_param_setters = []
        global_additional_imports = set()
        mime_type = None
        processor = common.RustSdkProcessor()
        # Process parameters
        for param in openapi_spec["paths"][path].get(
            "parameters", []
        ) + spec.get("parameters", []):
            (xparam, setter) = common.get_rust_param_dict(param, "sdk")
            if xparam:
                # for i.e. routers/{router_id} we want local_name to be `id` and not `router_id`
                if (
                    xparam["location"] == "path"
                    and xparam["name"] == f"{res_name.lower()}_id"
                ):
                    xparam["local_name"] = "id"
                global_params[xparam["name"]] = xparam
                global_additional_imports.update(xparam["additional_imports"])
            if setter:
                global_param_setters.append(setter)

        # Process body
        request_body = spec.get("requestBody")
        # List of operation variants (based on the body)
        operation_variants = []
        if request_body:
            content = request_body.get("content", {})
            json_body_schema = content.get("application/json", {}).get(
                "schema"
            )
            if json_body_schema:
                mime_type = "application/json"
                # response_def = json_body_schema
                if "oneOf" in json_body_schema:
                    # There is a choice of bodies. It can be because of
                    # microversion or an action (or both)
                    # For action we should come here with command_type="action" and command_name must be the action name
                    # For microversions we build body as enum
                    # So now try to figure out what the discriminator is
                    discriminator = json_body_schema.get(
                        "x-openstack", {}
                    ).get("discriminator")
                    if discriminator == "microversion":
                        logging.debug("Microversion discriminator for bodies")
                        for variant in json_body_schema["oneOf"]:
                            operation_variants.append({"body": variant})
                        # operation_variants.extend([{"body": x} for x in json_body_schema(["oneOf"])])
                else:
                    operation_variants.append({"body": json_body_schema})
        else:
            # Explicitly register variant without body
            operation_variants.append({"body": None})
        for operation_variant in operation_variants:
            logging.debug("Processing variant %s" % operation_variant)

            request_key = None
            request_def = None
            subtypes = {}
            params = copy.deepcopy(global_params)
            param_setters = global_param_setters.copy()
            additional_imports = copy.deepcopy(global_additional_imports)
            class_name = res_name.title()
            operation_body = operation_variant.get("body")
            mod_name = (
                args.alternative_module_name
                or args.command_type.value
                or method
            )

            if operation_body:
                try:
                    request_def, request_key = common.find_resource_schema(
                        operation_body, None, resource_name=res_name
                    )
                except Exception:
                    logging.warn("Cannot identify body")
                    return
                min_ver = operation_body.get("x-openstack", {}).get("min-ver")
                if min_ver:
                    mod_name += "_" + min_ver.replace(".", "")
                if not request_def:
                    # Not able to identity where the resource schema is. Take the whole schema as is
                    request_def = json_body_schema
                if request_def:
                    # body_model = types.get_type_from_schema(request_def)
                    body_model = types.JsonSchemaParser().parse(operation_body)
                continue
                processor.set_body_model(body_model)
                # continue

                # if request_def.get("type") == "object":
                #    # Our TL element is an object. This is what we expected
                #    required_props = request_def.get("required", [])
                #    for k, el in request_def.get("properties", {}).items():
                #        (
                #            xparam,
                #            setter,
                #            xsubtypes,
                #        ) = common.get_rust_body_element_dict(
                #            k, el, k in required_props, "sdk"
                #        )

                #        if xparam:
                #            params[xparam["name"]] = xparam
                #        if xsubtypes:
                #            subtypes.update(xsubtypes)
                #        if setter:
                #            param_setters.append(setter)

                #        additional_imports.update(xparam["additional_imports"])
            if method == "patch":
                # There might be multiple supported mime types. We only select ones we are aware of
                if "application/openstack-images-v2.1-json-patch" in content:
                    mime_type = "application/openstack-images-v2.1-json-patch"
                elif "application/json-patch+json" in content:
                    mime_type = "application/json-patch+json"
                else:
                    raise RuntimeError(
                        "No supported mime types for patch operation found"
                    )

            # class_name = "".join(
            #    x.title() for x in operation_id.split(".")[0].split("_")
            # )
            mod_path = common.get_rust_sdk_mod_path(
                args.service_type,
                args.api_version,
                args.alternative_module_path or path,
            )

            response_def = None
            response_key = None
            # Get basic information about response
            if method.upper() != "HEAD":
                for code, rspec in spec["responses"].items():
                    if not code.startswith("2"):
                        continue
                    content = rspec.get("content", {})
                    if "application/json" in content:
                        response_spec = content["application/json"]
                        try:
                            (
                                response_def,
                                response_key,
                            ) = common.find_resource_schema(
                                response_spec["schema"],
                                None,
                                resource_name=res_name.lower(),
                            )
                        except Exception:
                            # Most likely we have response which is oneOf.
                            # For the SDK it does not really harm to ignore
                            # this.
                            pass
                            # response_def = (None,)
                            response_key = None

            context = dict(
                operation_id=operation_id,
                operation_type=spec.get(
                    "x-openstack-operation-type", args.command_type
                ),
                command_description=spec.get("description"),
                class_name=class_name,
                sdk_service_name=common.get_rust_service_type_from_str(
                    args.service_type
                ),
                url=path[1:] if path.startswith("/") else path,
                method=method,
                processor=processor,
                params=params,
                request_key=args.request_key or request_key,
                response_key=args.response_key or response_key,
                response_list_item_key=args.response_list_item_key,
                path_params={
                    k: v for k, v in params.items() if v["location"] == "path"
                },
                query_params={
                    k: v for k, v in params.items() if v["location"] == "query"
                },
                body_params={
                    k: v for k, v in params.items() if v["location"] == "body"
                },
                static_lifetime=bool(
                    len(
                        list(
                            v
                            for v in params.values()
                            if v["location"] in ["path", "query", "body"]
                            and "'a" in v["type"]
                        )
                    )
                    > 0
                ),
                param_setters=param_setters,
                mime_type=mime_type,
                additional_imports=additional_imports,
                subtypes=subtypes,
            )

            work_dir = Path(target_dir, "rust", "openstack_sdk", "src")
            # mod_name
            impl_path = Path(
                work_dir,
                "api",
                "/".join(mod_path),
                f"{mod_name}.rs",
            )

            # Generate methods for the GET resource command
            self._render_command(
                context,
                "rust_sdk/impl.rs.j2",
                impl_path,
            )

            self._format_code(impl_path)

            yield (mod_path, mod_name, path)

    def generate_mod(
        self, target_dir, mod_path, mod_list, url, resource_name, service_name
    ):
        work_dir = Path(target_dir, "rust", "openstack_sdk", "src")
        impl_path = Path(
            work_dir,
            "api",
            "/".join(mod_path[0:-1]),
            f"{mod_path[-1]}.rs",
        )

        context = dict(
            mod_list=mod_list,
            mod_path=mod_path,
            url=url,
            resource_name=resource_name,
            service_name=service_name,
        )

        # Generate methods for the GET resource command
        self._render_command(
            context,
            "rust_sdk/mod.rs.j2",
            impl_path,
        )

        self._format_code(impl_path)
